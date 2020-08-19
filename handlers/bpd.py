import os
import sys
import locale
import logging
import requests
from time import sleep
from . import OfficerMatcher
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ResponseBot'))
from responsebot.handlers import BaseTweetHandler, register_handler
from responsebot.models import TweetFilter

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


def generate_tweet(officer):
    text = ""
    if officer.assignments.count() > 0 and officer.assignments[0].job.job_title != 'Not Sure':
            text += f"{officer.assignments[0].job.job_title} "
    text += f"{officer.full_name()} ({officer.unique_internal_identifier.upper()})"
    if officer.salaries and len(officer.salaries) > 0:
        total_pay = officer.salaries[0].salary - officer.salaries[0].overtime_pay
        text += f" made {locale.currency(total_pay, grouping=True)} in {officer.salaries[0].year}."
    else:
        text += "."
    if officer.incidents:
        if len(officer.incidents) == 1:
            text += f" {officer.last_name} was involved in 1 incident."
        else:
            text += f" {officer.last_name} was involved in {len(officer.incidents)} incidents."
    text += f" Full profile: https://bpdwatch.com/officer/{officer.id}."
    logging.info(f"Generated tweet: {text}")
    return text


@register_handler
class BPDHandler(BaseTweetHandler):
    def __init__(self, client):
        super().__init__(client)
        self.matcher = OfficerMatcher()

    def get_filter(self):
     return TweetFilter(track=['@whoisbpd'])

    def on_tweet(self, tweet):
        def parse_tweet(_tweet):
            logging.info(f"Parsing tweet: {_tweet.text}")
            # remove periods, lower case, remove double+ spaces bw words
            tweet_text = ' '.join(_tweet.text.lower().replace('.','').split())
            officers = self.matcher.match_officers(tweet_text)
            # Check text of any links
            for link in _tweet.entities['urls']:
                r = requests.get(link['expanded_url'])
                if r.status_code == 200:
                    officers |= self.matcher.match_officers(r.text)
            return officers

        matched_officers = parse_tweet(tweet)
        # Check text of quote retweet
        if tweet.is_quote_status:
            matched_officers |= parse_tweet(tweet.quoted_status)

        for officer in matched_officers:
            tweet_text = f'@{tweet.user.screen_name} ' + generate_tweet(officer)
            self.client.tweet(
                tweet_text,
                in_reply_to=tweet.id
            )
            sleep(1)
    
    def on_direct_message(self, message):
        msg_text = message.message_create['message_data']['text']
        logging.info(f"Parsing direct message: {msg_text}")
        
        # remove periods, lower case, remove double+ spaces bw words
        msg_text = ' '.join(msg_text.lower().replace('.','').split())
        matched_officers = self.matcher.match_officers(msg_text)
        
        # Check text of any links
        for link in message.message_create['message_data']['entities']['urls']:
            r = requests.get(link['expanded_url'])
            if r.status_code == 200:
                matched_officers |= self.matcher.match_officers(r.text)
        
        for officer in matched_officers:
            self.client.direct_message(
                user_id=int(message.message_create['sender_id']),
                text=generate_tweet(officer)
            )
            sleep(1)