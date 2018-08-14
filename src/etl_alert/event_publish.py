import pymongo
from datetime import datetime, timedelta
import random 
import time 
import uuid
import logging
from etl_alert import ConfigSet, log_config

FILENAME = "config.yml"
DUR_POOL = range(10)
STATUS_POOL = ["SUCCESS", "ERROR"]
JOB_TYPE_POOL = ["ETL", "NON-ETL"]
JOB_NAME_POOL = ["extractor", "transformer", "loader"]
ERROR_MSG_POOL = range(10)

log_config()
logger = logging.getLogger("etl_publish")

class EventRecordBuilder(object):
    record = {}
    def with_uuid(self):
        self.record['_id'] = str(uuid.uuid4())
        return self

    def with_random_job(self):
        self.record['job'] = random.choice(JOB_NAME_POOL)
        return self 

    def with_random_job_type(self):
        self.record['job_type'] = random.choice(JOB_TYPE_POOL)
        return self

    def with_random_status(self):
        self.record['status'] = random.choice(STATUS_POOL)
        return self

    def with_random_error_msg(self):
        msg = "this is a demo error messgae number#{}.".format(
            random.choice(ERROR_MSG_POOL))
        self.record['error_message'] = msg
        return self

    def with_random_duration(self):
        self.record['duration_minutes'] = random.choice(DUR_POOL)
        return self

    def with_random_start_time(self):
        rand_time = datetime.utcnow()
        self.record['start_time'] = rand_time
        return self
    
    def build(self):
        return self.record 

class MongoAtlasConnector(object):
    def __init__(self, conf):
        url = conf.url()
        db = conf.db()
        coll = conf.coll()
        self.client = pymongo.MongoClient(url)
        self.db = self.client[db]
        self.coll = self.db[coll]
    
    def insert_one(self, record):
        self.coll.insert_one(record)

    def find_one(self):
        record = self.coll.find_one()
        logger.debug("find one record:\n%s" % record)
        return record

    def set_collection(self, collection_name):
        self.coll = self.db[collection_name]

    
class EventMetaDataProducer(object):

    def __init__(self, connector):
        self.mongo_connector = connector
        
    def generate_one_record(self):
        record_builder = EventRecordBuilder()
        record = record_builder         \
            .with_uuid()                \
            .with_random_job()          \
            .with_random_job_type()     \
            .with_random_error_msg()    \
            .with_random_status()       \
            .with_random_start_time()   \
            .with_random_duration()     \
            .build()
    
        return record 

    def produce(self):
        record = self.generate_one_record()
        print("#[debug]:> producing random record:\n%s\n" % record)
        self.mongo_connector.insert_one(record)

def main():
    conf = ConfigSet(FILENAME)
    conn = MongoAtlasConnector(conf)
    event_producer = EventMetaDataProducer(conn)
    while True:
        event_producer.produce()
        time.sleep(3+random.random()*2)

if __name__ == "__main__":
    main()