import os
import abc
import json
import logging
import yaml
from collections import namedtuple
import requests
import pprint 
from etl_alert.event_publish import MongoAtlasConnector
from etl_alert import log_config, ConfigSet

CONFIG_FILENAME = 'config.yml'
Event = namedtuple('Event', ['job_name', 'status', 'start_time', 'duration', 'err_msg'])
log_config()
logger = logging.getLogger("etl_alert")


class MetadataWatcher(object):
    def __init__(self, connector):
        self.connector = connector
        
    def open_cursor(self, pipeline=None, resume_after=None):
        cursor = self.connector.coll.watch(pipeline=pipeline, resume_after=resume_after)
        return cursor

    def watch_and_process(self, collection_name=None, pipeline=None, processor=None, resume_after=None):
        """streaming job"""
        if collection_name:
            self.connector.set_collection(collection_name)

        cursor = self.open_cursor(pipeline=pipeline, resume_after=resume_after)
        logger.debug("start watching change stream: \n")
        self.pull_stream_and_process(cursor, processor)

    @staticmethod
    def pull_stream_and_process(cursor, processor=None):
        with cursor as stream:
            for change in stream:
                logger.debug("read change stream: %s\n" % change['fullDocument'])
                if callable(processor):
                    processor(change['fullDocument'])


class EventMetadataWatcher(MetadataWatcher):
    def __init__(self, connector):
        super().__init__(connector)
        self.collection_name = self.connector.coll.name

        self.pipeline = [
            {
                '$project': {'fullDocument': 1}
            },
            {
                '$match': {
                    '$and': [
                        {'fullDocument.job_type': 'ETL'},
                        {'fullDocument.status': {'$ne': 'SUCCESS'}}
                    ]
                } 
            }
        ]

    def watch_and_alert(self, alert=None, resume_after=None):
        self.watch_and_process(collection_name=self.collection_name, pipeline=self.pipeline, processor=alert, resume_after=resume_after)

    @staticmethod
    def alert_via_slack(stream):
        slack_alerter = SlackAlerter()
        attached_msg = EventMetadataWatcher.prepare_attached_msg(stream)
        slack_alerter.alert(attached_msg)

    @staticmethod
    def convert_to_event_tuple(event):
        job_name = event['job']
        status = event['status']
        err_msg = event['error_message']

        time_format = "%a %b %d %H:%M:%S %Y"
        start_time = event['start_time'].strftime(time_format)
        duration = "{0:.2f}s".format(event['duration_minutes']*60)

        event_tuple = Event(job_name, status, start_time, duration, err_msg)
        return event_tuple

    @staticmethod
    def prepare_attached_msg(event):
        event_tuple = EventMetadataWatcher.convert_to_event_tuple(event)
        text = json.dumps(event_tuple._asdict())
        logger.debug("event message is %s", text)
        warning_color = "#ff0000"
        title = "ETL job *{}*".format(event_tuple.job_name)
        attached_msg = [
            {
                "color" : warning_color,
                "title" : title,
                'text': text,
                "mrkdwn_in": ['text']
            }
        ]
        return attached_msg


class Alerter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def alert(self, message):
        """abstract method to send an alert message to destination"""


class SlackAlerter(Alerter):
    webhook_url = os.getenv(
        'WEB_HOOK_URL', 
        'https://hooks.slack.com/services/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'
        )

    def alert(self, message):
        """
        send a message to the bearing channel
        :param message: message in format of attachements
        :return:
        """
        logger.debug("send message \"%s\"\n" % message)
        total_msg = {"text": "A ETL job fails:" }
        total_msg["attachments"] = message
        response = requests.post(
            self.webhook_url, 
            data=json.dumps(total_msg), 
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            raise ValueError(
                'Request to slack returned an error %s, the response is:\n%s'
                % (response.status_code, response.text)
            )

def config_atlas_connector():
    conf = ConfigSet(CONFIG_FILENAME)
    connector = MongoAtlasConnector(conf)
    return connector

def test_slack_service():
    connector = config_atlas_connector()
    watcher = EventMetadataWatcher(connector)
    watcher.watch_and_alert(EventMetadataWatcher.alert_via_slack)

def test_print_service():
    connector = config_atlas_connector()
    watcher = EventMetadataWatcher(connector)
    watcher.watch_and_alert()

if __name__ == "__main__":
    test_slack_service()
