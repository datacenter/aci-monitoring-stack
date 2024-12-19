import multiprocessing
import mgclient
import os
import logging


# Configure the root logger
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [Thread ID: %(thread)d] - %(message)s')

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a console handler and set its level to DEBUG
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create a formatter and set it for the handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Thread ID: %(thread)d] - %(message)s')
ch.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(ch)

host = os.environ['MEMGRAPH_SVC_HOST']
port = int(os.environ['MEMGRAPH_SVC_PORT'])


def wipe_db():
    # Delete everything for now
    conn = mgclient.connect(host=host, port=port)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("MATCH (n) DETACH DELETE n;")
    cursor.execute("CALL schema.assert({}, {}, {}, true) YIELD action, key, keys, label, unique RETURN action, key, keys, label, unique;")
    cursor.close()
    conn.close()
    
def in_memory_analytical():
    conn = mgclient.connect(host=host, port=port)
    cursor = conn.cursor()
    conn.autocommit = True
    cursor.execute("STORAGE MODE IN_MEMORY_ANALYTICAL")
    cursor.close()
    conn.close()

def in_memory_transactional():
    conn = mgclient.connect(host=host, port=port)
    cursor = conn.cursor()
    conn.autocommit = True
    cursor.execute("STORAGE MODE IN_MEMORY_TRANSACTIONAL")
    cursor.close()
    conn.close()
    
def execute_load(q):
    conn = mgclient.connect(host=host, port=port)
    cursor = conn.cursor()
    logger.debug("execute: %s", q)
    max_retries=10
    for attempt in range(max_retries):
        try:
            cursor.execute(q)
            conn.commit()
            break
        except Exception as e:
            logger.error("Transaction failed %s", str(e))
    cursor.close()            
    conn.close()

def execute_indexes(q):
    conn = mgclient.connect(host=host, port=port)
    cursor = conn.cursor()
    max_retries=10
    for attempt in range(max_retries):
        try:
            conn.autocommit = True
            cursor.execute(q)
            break
        except Exception as e:
            logger.error("Transaction failed %s", str(e))
    cursor.close()
    conn.close()

def db_load(fabric_backup_folder):

    csv_folder = os.path.join(fabric_backup_folder, 'csv')
    logger.info("Loading Indexes")
    with open(csv_folder + "/indexes", 'r') as f:
        lines = f.readlines()
        with multiprocessing.Pool(1) as pool:
            pool.map(execute_indexes, lines)
    logger.info("Loading Nodes")
    with open(csv_folder + "/nodes", 'r') as f:
        lines = f.readlines()
        with multiprocessing.Pool(1) as pool:
            pool.map(execute_load, lines)
    logger.info("Loading Edges")
    with open(csv_folder + "/edges", 'r') as f:
        lines = f.readlines()
        with multiprocessing.Pool(1) as pool:
            pool.map(execute_load, lines)
    logger.info("DB Import Completed")