import os
import csv
from pyaci import Backup, Node, options, filters, errors
import const
import logging
from  shutil import rmtree
import yaml
import urllib3
import requests
from time import sleep
import paramiko
import tarfile
from db_load import db_load, wipe_db, in_memory_analytical, in_memory_transactional

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
root_backup_folder = const.root_backup_folder
# The way pyACI works with options.subtree is that it will return the object and all its children and the children of the children and so on
# So by just looping the object children we get the entire MIT Tree

def traverse_tree(objects,callback):
    """Traverse the pyACI MIT Tree recursively 

    Args:
        objects (_type_): PyACI Object to process
        callback (function): Function to process the object being traversed
    """
    for o in objects:
        callback(o)
        if hasattr(o, "Children"):
            traverse_tree(o.Children,callback)
            
def load_objects(o, data):
    _, fabric_backup_folder = folder_paths(data['fabric_id'])
    csv_folder = os.path.join(fabric_backup_folder, 'csv')
    """ This function is called by the traverse_tree function to process each object in the MIT tree.

    Args:
        o (pyACI Mo): The PyACI Object MIT object. It will be traversed to convert the Backup into a set of CSV files and LOAD Statement.
        data (dict): This dic will be loaded with all the data that will be written to disk
        fabric (string): Name of the fabric being processed

    """
    if o.ClassName not in const.exclude_classes:
        if o.ClassName not in data['classes']:
            data['classes'].add(str(o.ClassName))
            if o.ClassName not in dict(const.RelationshipToLocal | const.RelationshipFromLocal | const.RelationshipFromGlobal | const.RelationshipToGlobal ):
                # Create the Header for the #Class CSV File
                data['csv_nodes'][o.ClassName] = []
                # Enrich the node CSV with a mainstat property for Grafana Visualization
                data['csv_nodes'][o.ClassName].append(o.NonEmptyPropertyNames + ['fabric', 'mainstat'])
                load_command = 'LOAD CSV FROM "' + csv_folder +'/{}.csv" WITH HEADER AS row CREATE (p:{}) SET p += row'.format(str(o.ClassName),str(o.ClassName))
                data['load_nodes'].append(load_command)
        
        # If the class is a relationship class we need to handle it differently and re-traverse the tree to find the target class
        if o.ClassName in dict(const.RelationshipToLocal | const.RelationshipFromLocal | const.RelationshipFromGlobal | const.RelationshipToGlobal ):
            data['relationships'].append(o)
            
        else:
            properties = []
            for p in o.NonEmptyPropertyNames:

                # At times the dn is set to "" in the backup so we get the Dn from pyACI instead
                if p == 'dn':
                    properties.append(o.Dn)
                else:
                    properties.append(getattr(o,p))
                    
            properties.append(data['fabric_id'])
            
            # Add the mainstat attribute
            if hasattr(o,"ip"):
                properties.append(o.ip)
            elif hasattr(o,"name"):
                properties.append(o.name)
            else:
                properties.append("")
            # Handle the matchExpression property that has quotas in it and breaks Cypher queries

            data['csv_nodes'][o.ClassName].append(properties)
            
            pc = o.Parent.ClassName + "-" + o.ClassName
            if pc not in data['parent-child-rel'].keys():
                data['parent-child-rel'][pc]=[]
                load_command = 'LOAD CSV FROM "'+ csv_folder +'/parent-child-{}-{}.csv" NO HEADER AS row MATCH (p:{}),(c:{}) WHERE p.dn=row[1] AND c.dn=row[2] AND p.fabric=row[0] AND c.fabric=row[0] CREATE (p)-[r:IS_PARENT]->(c)'.format(o.Parent.ClassName,o.ClassName,o.Parent.ClassName,o.ClassName)
                data['load_edges'].append(load_command)
            
            data['parent-child-rel'][pc].append([data['fabric_id'],o.Parent.Dn,o.Dn])
        
def create_non_pc_rel(data):
    _, fabric_backup_folder = folder_paths(data['fabric_id'])
    csv_folder = os.path.join(fabric_backup_folder, 'csv')
    def generate_rel(key,rel_target_class):
        
        # The backup MO properties are not 1:1 to what you have in the API so we need to ALWAYS look at a backup file to be sure how to code the logic. 
        # Some Rel Classes have a tDn in the backup
        # Some put the name of the target object in a property called tn<ClassName>Nameso but the 1st letter is capitalized. i.e. tnVzBrCPName
        npcr = []
        rel_target_prop = 'tn' + rel_target_class[0].upper() + rel_target_class[1:] + 'Name'
        
        if hasattr(rel, "tDn") and rel.tDn != None:
            
            # Handle Physical Port to Port Group: 'infraRsAccBaseGrp' arget_class is 'infraAccBaseGrp' that is grouping together 
            # infraAccBndlGrp and infraAccPortGrp and this is what is actually stored in the backup. 
            
            if rel.ClassName == 'infraRsAccBaseGrp':
                if rel.tDn.startswith('uni/infra/funcprof/accportgrp-'):
                    rel_target_class = "infraAccPortGrp"
                elif rel.tDn.startswith('uni/infra/funcprof/accbundle-'):
                    rel_target_class = "infraAccBndlGrp"
                
            
            # Handle Physical Domain to AAEP: 'infraRsDomP' Target_class is 'infraADomP' that is grouping together 
            # All the possible Pys Domains.
            if rel.ClassName == 'infraRsDomP':
                if rel.tDn.startswith('uni/phys-'):
                    rel_target_class = "physDomP"
                elif rel.tDn.startswith('uni/l3dom-'):
                    rel_target_class = "l3extDomP"
                elif rel.tDn.startswith('uni/vmmp-'):
                    rel_target_class = "vmmDomP"
            
            key += rel.Parent.ClassName + "-" + rel_target_class
            if key not in data['non-parent-child-rel'].keys():
                data['non-parent-child-rel'][key] = []
                load_command = 'LOAD CSV FROM "'+ csv_folder + '/{0}.csv" NO HEADER AS row MATCH (s:{1}),(t:{2}) WHERE s.dn=row[1] AND t.dn=row[2] AND s.fabric=row[0] AND t.fabric=row[0] CREATE (s)-[r:{3}]->(t)'.format(key,rel.Parent.ClassName,rel_target_class,rel.ClassName)
                data['load_edges'].append(load_command)
                
            npcr = [data['fabric_id'] , rel.Parent.Dn  , rel.tDn]
            data['non-parent-child-rel'][key].append(npcr)
            
        elif hasattr(rel, rel_target_prop):
            
            target_name = getattr(rel, rel_target_prop).replace("'","")
            if target_name == '':
                target_name = 'default'            
            edge_direction = '(s)-[r:{} {} ]->(t)'.format(rel.ClassName, ' {target: row[3] }')

            
            key += rel.Parent.ClassName + "-" + rel_target_class
            
            # Handle the contracts in a special way and override the default file name and relationship direction.
            if rel.ClassName == 'fvRsProv':
                key += '-fvRsProv'
                edge_direction = '(s)-[r:{} {} ]->(t)'.format(rel.ClassName, ' {target: row[3] }')
            elif rel.ClassName == 'fvRsCons':
                key += '-fvRsCons'
            
            key += rel.Parent.ClassName + "-" + rel_target_class
            
            if key not in data['non-parent-child-rel'].keys():
                data['non-parent-child-rel'][key] = []
                load_command = 'LOAD CSV FROM "'+ csv_folder + '/{0}.csv" NO HEADER AS row \
                MATCH (s:{1}) WHERE s.dn=row[1] AND s.fabric=row[0] \
                OPTIONAL MATCH (t1:{2}) WHERE t1.name=row[3] AND t1.dn STARTS WITH row[2] AND t1.fabric=row[0] \
                OPTIONAL MATCH (t2:{2}) WHERE t2.name=row[3] AND t2.dn STARTS WITH "uni/tn-common" AND t2.fabric=row[0] \
                OPTIONAL MATCH (t3:{2}) WHERE t3.name=row[3] AND t3.dn STARTS WITH "uni/fabric" AND t3.fabric=row[0] \
                OPTIONAL MATCH (t4:{2}) WHERE t4.name=row[3] AND t4.dn STARTS WITH "uni/infra" AND t4.fabric=row[0] \
                OPTIONAL MATCH (t5:MissingTarget) WHERE t5.fabric=row[0] \
                WITH row, s, COALESCE(t1, t2, t3, t4, t5) AS t \
                WHERE s IS NOT NULL AND t IS NOT NULL \
                CREATE {3}'.format(key,rel.Parent.ClassName,rel_target_class,edge_direction)
                data['load_edges'].append(load_command)
        
            npcr = [data['fabric_id'] , rel.Parent.Dn , "/".join(rel.Parent.Dn.split('/')[:2]) , target_name]
            data['non-parent-child-rel'][key].append(npcr)
            
    for rel in data['relationships']:

        if rel.ClassName in const.RelationshipToLocal.keys():
            rel_target_class = const.RelationshipToLocal[rel.ClassName]
            key = 'lrs-'
            generate_rel(key,rel_target_class)
            
        elif rel.ClassName  in const.RelationshipFromGlobal.keys():
            rel_target_class = const.RelationshipFromGlobal[rel.ClassName]
            key = 'grs-'
            generate_rel(key,rel_target_class)
            
        else:
            raise Exception ("Unknown Relationship: ", rel.ClassName)
            
def write_to_disk(data,fabric_backup_folder):
    csv_folder = os.path.join(fabric_backup_folder, 'csv')
    if not os.path.exists(csv_folder):
        os.makedirs(csv_folder)
    # Create the indexes on the classes 
    with open(csv_folder +'/indexes', 'w') as f:
        for c in data['classes']:
            index = ("CREATE INDEX ON :{0}\nCREATE INDEX ON :{0}(dn)\nCREATE INDEX ON :{0}(fabric)\nCREATE INDEX ON :{0}(name)\n".format(c))
            f.write(index)
    
    # Write the Nodes LOAD Queries
    
    with open(csv_folder + '/nodes', 'w') as f:
        for i in data['load_nodes']:
            f.write(i + ";\n")
            
    # Write the Edges LOAD Queries
    with open(csv_folder +'/edges', 'w') as f:
        for i in data['load_edges']:
            f.write(i + ";\n")
            
    # Write the Nodes CSV
    for k,v in data['csv_nodes'].items():
        with open(csv_folder +'/{}.csv'.format(k), 'w') as f:
            wr = csv.writer(f,quoting=csv.QUOTE_ALL)
            wr.writerows(v) 
                

    # Write the parent-child CSV Edges
    for k,v in data['parent-child-rel'].items():
        with open(csv_folder +'/parent-child-{}.csv'.format(k), 'w',newline='') as f:
            wr = csv.writer(f, quoting=csv.QUOTE_ALL)
            wr.writerows(v) 
    
    ## Write the non-parent-child CSV Edges
    for k,v in data['non-parent-child-rel'].items():
         with open(csv_folder + '/' + k + '.csv', 'w') as f:
            wr = csv.writer(f, quoting=csv.QUOTE_ALL)
            wr.writerows(v) 

def process_backups(backups):
    for fabric, backup_file in backups.items():
        fabric_meta, fabric_backup_folder = folder_paths(fabric)
        data = {
            'classes': set(),
            'parent-child-rel': {},
            'relationships': [], # this holds the relationship classes that are not parent-child for further processing
            'non-parent-child-rel': {},
            'load_nodes': [],
            'load_edges': [],
            'csv_nodes': {},
            'csv_edges': [],
            'fabric_id': ""
        }
        data['fabric_id']=fabric
        
        #Add a special case for the MissingTarget Objects
        data['classes'].add("MissingTarget")
        data['csv_nodes']["MissingTarget"] = []
        # Enrich the node CSV with a mainstat property for Grafana Visualization
        data['csv_nodes']["MissingTarget"].append(['fabric', 'mainstat'])
        # I really only need 1 MissingTarget node per fabric no other info is needed.
        data['csv_nodes']["MissingTarget"].append([data['fabric_id'],data['fabric_id']])
        csv_folder = os.path.join(fabric_backup_folder, 'csv')
        load_command = 'LOAD CSV FROM "' + csv_folder +'/MissingTarget.csv" WITH HEADER AS row CREATE (p:MissingTarget) SET p += row'
        data['load_nodes'].append(load_command)
        
        
        logger.info("PyACI: Loading Backup in Memory for Fabric %s",fabric)
        b = Backup(backup_file, aciMetaFilePath=fabric_meta).load()
        logger.info("PyACI: Completed Loading Backup in Memory for Fabric %s",fabric)

        
        logger.info("Process Nodes and Parent Child Relationships for Fabric %s",fabric)
        traverse_tree(b.Children, lambda node: load_objects(node, data))
        
        logger.info("Process Non Parent Child Relationships for Fabric %s",fabric)
        create_non_pc_rel(data)
        write_to_disk(data, fabric_backup_folder)
        logger.info("Done, you can now import the data in Memgraph for Fabric %s",fabric )

def load_config():
    with open('/etc/backup2graph/config.yaml') as f:
        fabrics = yaml.load(f.read(), Loader=yaml.FullLoader)
    return fabrics['fabrics']

def init(fabrics):
    # wipe the backup folder if it exists
    if os.path.exists(root_backup_folder):
        for f in os.listdir(root_backup_folder):
            rmtree(os.path.join(root_backup_folder,f))
    
    # Load Fabric data and create folders and download the meta.json file
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    for fabric, data in fabrics.items():
        fabric_folder = os.path.join(root_backup_folder, fabric)        
        os.makedirs(fabric_folder)
        logger.info("Downloading ACI Metadata for %s", fabric)
        success = False
        for apic_url in data['apic']:
            try:
                requests.get(apic_url, verify=False, allow_redirects=True, timeout=5)
                success = True
                break
            except Exception as e:
                logger.error("Unable to Connect to APIC %s will try the next one if it exists", str(e))
        
        if success:
            meta_url = apic_url + '/acimeta/aci-meta.json'
            r = requests.get(meta_url, verify=False, allow_redirects=True)
            open(fabric_folder + '/aci-meta.json','wb').write(r.content)
            logger.info("ACI Metadata Downloaded")
        else:
            logger.error("Unable to Load Metadata for %s. This fabric will not be imported", fabric)

def copy_file_via_scp(local_path, remote_path, hostname, port, username, password):
    """Copy a file to a remote server via SCP.

    Args:
        local_path (str): Path to the local file.
        remote_path (str): Path on the remote server.
        hostname (str): Remote server hostname or IP address.
        port (int): Port number for SSH.
        username (str): Username for SSH.
        password (str): Password for SSH.
    """
    count = 5
    success = False
    while count > 0:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, port, username, password)
            sftp = ssh.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            ssh.close()
            logger.info("File copied successfully from %s:%s", hostname, remote_path)
            success = True
            break
        except Exception as e:
            logger.error("Failed to copy file from %s:%s. Will try %d times more. Error: %s", hostname, remote_path, count, str(e))
            count -= 1
            sleep(5)

    return success

def folder_paths(fabric):
    fabric_meta = os.path.join(root_backup_folder, fabric,'aci-meta.json')
    fabric_backup_folder = os.path.join(root_backup_folder, fabric, "backups")
    return fabric_meta, fabric_backup_folder

def get_backups(fabrics):
    backups = {}
    for fabric, data in fabrics.items():
        fabric_meta, fabric_backup_folder = folder_paths(fabric)
        
        # If the directory alredy exist wipe the current backup data
        if os.path.exists(fabric_backup_folder):
            rmtree(fabric_backup_folder)
        
        os.makedirs(fabric_backup_folder)
        
        if os.path.exists(fabric_meta):
            logger.info("Generating Backup For %s", fabric)
            
            for apic_url in data['apic']:
                try:
                    apic = Node(apic_url, aciMetaFilePath=fabric_meta,timeout=5)
                    apic.methods.Login(data['username'], data['password']).POST()
                    
                    # Get the current last backup as it takes some time to generate one and we need to be sure we pick the last
                    old_config_job = apic.methods.ResolveClass('configJob').GET(
                        **options.orderBy('configJob.executeTime|desc')
                        & options.page("0") 
                        & options.pageSize("1") 
                        & options.filter(filters.Wcard('configJob.fileName', const.config_export_policy_name)))
                    if len(old_config_job) > 0:
                        old_config_job_name = old_config_job[0].fileName
                    else:
                        old_config_job_name = "no_file"
                        
                        
                    # Trigger a new backup
                    apic.mit.polUni().fabricInst().configExportP(name=const.config_export_policy_name,format='json', snapshot='yes', adminSt='triggered').POST()
                
                    count = 5
                    while count > 0:
                        
                        # Get the fileName for the just exectuted export.
                        new_config_job = apic.methods.ResolveClass('configJob').GET(
                            **options.orderBy('configJob.executeTime|desc')
                            & options.page("0") 
                            & options.pageSize("1") 
                            & options.filter(filters.Wcard('configJob.fileName', const.config_export_policy_name)))
                        
                        if len(new_config_job) == 0:
                            count -= 1
                            logger.info("No Backup Exists, will try %d more times", count)
                            sleep(5)
                        
                        else:
                            new_config_job_name = new_config_job[0].fileName
                            if new_config_job_name == old_config_job_name:
                                count -= 1
                                logger.info("New Backup not yet ready, will try %d more times", count)
                                sleep(5)

                            else:
                                parsed = urllib3.util.parse_url(apic_url)
                                backup_file_path = os.path.join(fabric_backup_folder, new_config_job_name)
                                
                                if copy_file_via_scp(backup_file_path,
                                                "/data2/snapshots/" + new_config_job_name,
                                                parsed.host,
                                                22,
                                                data['username'],
                                                data['password']
                                                ):
                                    if backup_file_path.endswith(".tar.gz"):
                                        with tarfile.open(backup_file_path, "r:gz") as tar:
                                            tar.extractall(path=fabric_backup_folder,filter="data")
                                        logger.info("Decompressed the backup file %s", new_config_job_name)
                                        
                                        # Remove the '.tar.gz' part
                                        backup_file = backup_file_path[:-7] + '_1.json'
                                        backups[fabric] = backup_file
                                        count = 0 # Copy success stop the loop
                                        
                    # Delete all the snapshots we have created even stale ones
                    # Get the fileName for the just exectuted export.
                    const.config_export_policy_name
                    
                    snapshots = apic.methods.ResolveClass('configSnapshot').GET(
                        **options.rspPropInclude('config-only') &
                        options.filter(filters.Wcard('configSnapshot.fileName', const.config_export_policy_name))
                        )
                    for snapshot in snapshots:
                        snapshot.retire="true"
                        snapshot.POST()
                        logger.info("Deleted Snapshot %s", snapshot.name)
                    # Break also the for loop trying all the APICs
                    break
                            
                except Exception as e:
                    logger.error("Unable to Connect to Fabric %s APIC %s will try the next one if it exists. Error %s",fabric, apic_url, str(e))
                        
        else:
            logger.error("aci-meta file does not exist for fabric %s, this fabric will not be processed", fabric)
    return backups

# Load the config map having the ACI access details
fabrics = load_config()

# Download metadata and clean up directories
init(fabrics)

# Generate the backups
backups = get_backups(fabrics)

# Generate the CSV files to load in Memgraph
process_backups(backups)

# For now Wipe the DB
wipe_db()

#Load in Memgraph, analytical provides faster load times so I use this one
in_memory_analytical()

for fabric, backup_file in backups.items():
    _, fabric_backup_folder = folder_paths(fabric)
    logger.info("Start DB Import for %s", fabric)
    db_load(fabric_backup_folder)
    logger.info("Completed DB Import for %s", fabric)
# Load Done switch back to in_memory_transactional
in_memory_transactional()