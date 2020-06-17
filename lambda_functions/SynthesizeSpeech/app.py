# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import json
import time
import boto3
import random
import requests
import textwrap

polly_client = boto3.Session().client('polly')
s3 = boto3.resource('s3')

bucketName = os.environ.get('BUCKET_NAME')
filename = 'speech.mp3'

paperQuotesToken = os.environ.get('PAPER_QUOTES_TOKEN')

def getQuotes(tags):
    PAPERQUOTES_API_ENDPOINT = 'http://api.paperquotes.com/apiv1/quotes?tags={tags}&limit=50'.format(tags=tags)
    response = requests.get(PAPERQUOTES_API_ENDPOINT, headers={'Authorization': 'TOKEN {}'.format(paperQuotesToken)})

    if response.ok:
        quotes = json.loads(response.text).get('results')
        return random.choice(quotes)

def lambda_handler(event, context):
    print(event)
    body = json.loads(event['body'])

    voiceId = body['voiceId']

    if ('text' in body):
        text = body['text']

    if ('tags' in body):
        quote = getQuotes(body['tags'])
        text = quote['quote'] + ' by ' + quote['author']

    response = polly_client.synthesize_speech(
                VoiceId=voiceId,
                OutputFormat='mp3',
                Text = text)

    obj = s3.Object(bucket_name=bucketName, key=filename)
    obj.put(Body=response['AudioStream'].read(), ContentType='audio/mp3', ACL='public-read')

    url = "https://{bucket}.s3.amazonaws.com/{key}".format(bucket=bucketName, key=filename)
    text = textwrap.fill(text, 42, break_long_words=False)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "url": url,
            "text": text
        })
    }
