import logging
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / 'lib'))

from cluster import start_cluster
import utils

LEAF_NODE = 0
BRANCH_NODE_NO_VALUE = 1
BRANCH_NODE_WITH_VALUE = 2
EXTENSION_NODE = 3

node_encoding_keys = [LEAF_NODE, BRANCH_NODE_NO_VALUE, BRANCH_NODE_WITH_VALUE, EXTENSION_NODE]
node_count = lambda proof, key: len([e for e in proof if e[0] == key])

def main():
    """
        1. Spin up 5 nodes all using the same shard and iterate over each node 1 by 1
        2. Wait 3 blocks and sequentially query each node for access_key_view
        3. Extract proof from acess_key_view and validate structural proof traits
    """

    nodes = start_cluster(
    5, 0, 1, None,
    [["epoch_length", 10], ["block_producer_kickout_threshold", 60],
     ["chunk_producer_kickout_threshold", 60]], {})
    
    logging.info("Iterating over nodes to fetch arbitrary access key proofs")

    for node in nodes:

        utils.wait_for_blocks(node, count=3)
        logging.info("Blocks are being produced, sending access key view queries...")
        
        key_query_result = node.get_access_key(node.signer_key.account_id,
                                    node.signer_key.pk, proof=True)
        
        proof = key_query_result["result"]["proof"]
        
        logging.info("Fetched access key, validating for structural integrity....")

        ## Invariant testing

        assert len(proof) > 0; "Valid proof returned must have more than one node"

        for raw_node_encoding in proof:
            assert raw_node_encoding[0] in node_encoding_keys; "0th bit of proof must be valid trie node encoding"

        assert proof[-1][0] == LEAF_NODE; "The last raw trie node in a proof must be a leaf node"
        assert proof[0][0] == EXTENSION_NODE; "The first raw trie node in a proo must be an extension node"

        leaf_count = node_count(proof, LEAF_NODE)
        branch_count = node_count(proof, BRANCH_NODE_NO_VALUE) + node_count(proof, BRANCH_NODE_WITH_VALUE)

        assert leaf_count == 1; "There can not be more than one leaf node per proof"
        assert branch_count >= 1; "There must be at least one branch node per proof"

    logging.info("Testing complete, terminating nodes....")
    for node in nodes:
        node.kill()


if __name__ == "__main__":
    main()
