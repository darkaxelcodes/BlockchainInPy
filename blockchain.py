import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(nonce = 1, previous_hash = '0', metadata = 'The Genesis Block')
        self.nodes = set()
    
    def create_block(self, nonce, previous_hash, metadata):
        block = {'index' : len(self.chain)+1,
                 'timestamp' : str(((datetime.datetime.now()-datetime.datetime.utcfromtimestamp(0)).total_seconds())*1000.0),
                 'nonce' : nonce,
                 'previous_hash' : previous_hash,
                 'metadata' : metadata,
                 'transactions': self.transactions}
        self.transactions = []
        self.chain.append(block)
        return block
    
    def get_previous_block(self):
        return self.chain[-1]
    
    def proof_of_work(self,previous_nonce):
        nonce = 1
        found = False
        while found is False:
            #timestamp = ((datetime.datetime.now()-datetime.datetime.utcfromtimestamp(0)).total_seconds())*1000.0
            #operation = (((nonce**3/2 - previous_nonce**3/2) * timestamp) - timestamp) % 1000
            operation = (nonce**3/2 - previous_nonce**3/2)
            hash = hashlib.sha256(str(operation).encode()).hexdigest()
            if hash[:4] == '0000':
                found = True
            else:
                nonce += 1
        return nonce
    
    def hash(self,block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def add_transactions(self, sender, reciever, amount):
        self.transactions.append({'sender' : sender,
                                  'reciever' : reciever,
                                  'amount' : amount})
        return len(self.chain)+1
    
    def add_node(self,address):
        parsed_address = urlparse(address)
        self.nodes.add(parsed_address.netloc)
    
    def check_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get('http://{0}/get_chain'.format(node))
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

app = Flask(__name__)
node_address = str(uuid4()).replace('-', '')
blockchain = Blockchain()

@app.route('/mine_block', methods=['POST'])
def mine_block():
    json = request.get_json()
    metadata = json.get('metadata')
    previous_block = blockchain.get_previous_block()
    previous_block_hash = blockchain.hash(previous_block)
    previous_block_nonce = previous_block['nonce']
    nonce = blockchain.proof_of_work(previous_block_nonce)
    #dummy fixed miner fee from self to self
    blockchain.add_transactions(node_address, node_address, 1)
    current_block = blockchain.create_block(nonce,previous_block_hash,metadata)
    response = {'message' : 'Congratulations! The block has been mined.',
                'index' : current_block['index'],
                'timestamp' : current_block['timestamp'],
                'nonce' : current_block['nonce'],
                'previous_hash' : current_block['previous_hash'],
                'metadata' : current_block['metadata'],
                'transactions' : current_block['transactions']}
    return jsonify(response), 201

@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {'Blockchain' : blockchain.chain,
                'Blockchain height' : len(blockchain.chain)}
    return jsonify(response), 200

@app.route('/add_transactions', methods=['POST'])
def add_transactions():
    json = request.get_json()
    transaction_keys = ['sender', 'reciever', 'amount']
    if not all (keys in json for keys in transaction_keys):
        return "Some elements of the transaction are missing", 400
    index = blockchain.add_transactions(json['sender'], json['reciever'], json['amount'])
    response = {"message" : "The transasactions will be added to the block no. {0}".format(index)}
    return jsonify(response), 200

@app.route('/connect_nodes', methods=['POST'])
def connect_nodes():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return "No Nodes", 400
    else:
        for node in nodes:
            blockchain.add_node(node)
    response = {'message' : 'The nodes have been added the blockchain. The blockchain has now {0} nodes'.format(list(blockchain.nodes))}
    return jsonify(response), 201

@app.route('/check_chain', methods=['GET'])
def check_chain():
    is_chain_replaced = blockchain.check_chain()
    if is_chain_replaced:
        response = {'Message' : 'The chain was not update. IT has been replaced with the longest chain on the network'}
    else:
        response = {'Message' : 'The chain is up to date with the network.'}
    return jsonify(response), 200
    

app.run(host = '127.0.0.1', port = 5000)
    
            

