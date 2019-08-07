# -*- coding: utf-8 -*-

import string
import random
import json
import aiohttp
from abc import ABC, abstractmethod

import asyncio
import websockets




sendMessageMutation = """
	mutation sendMessage($body: String!, $originId: String!, $originThreadId: String!, $username: String!, $authorOriginId: String!, $authorAvatarUrl: String!, $attachments: [AttachmentInput!]!) {
		sendMessage(
		  input: {
			body: $body,
			originId: $originId,
			originThreadId: $originThreadId,
			author: {
			  username: $username, 
			  originId: $authorOriginId,
			  avatarUrl: $authorAvatarUrl
			},
			attachments: $attachments
		  }
		) {
		  id
		}
	  }"""
messageReceivedSubscription = """
	  subscription {
		  messageReceived {
			message {
			  body
			  id
			  originId
			  attachments {
				  type
				  sourceUrl
				  originId
				  id
			  }
			  thread {
				  id
				  originId
				  name
			  }
			  threadGroupId
			  author {
				  username
				  originId
				  avatarUrl
			  }
			}
			targetThreadId
		  }
		}"""
requestConfigurationRequest = """
	subscription confRequest($fields: [ConfigurationField!]!){
		configurationReceived(configuration:{fields: $fields}) {
		  fieldValues
		}
	  }"""

setInstanceStatusMutation = """
	mutation {
		setInstanceStatus(status:INITIALIZED) {
		  status
		  name
		}
	  }"""

class GQLClient():
    def __init__(self, ws_url, http_url, access_token):
        self.ws_url = ws_url
        self.http_url = http_url
        self.access_token = access_token

    async def connect(self, connected_callback, message_callback):
        async with websockets.connect(self.ws_url, subprotocols=["graphql-ws"]) as ws:
            self.ws = ws
            await ws.send(json.dumps({
                'type': 'connection_init',
                'payload': {'accessToken': self.access_token}}))
            await ws.recv()
            asyncio.ensure_future(connected_callback())
            async for msg in ws:
                await message_callback(json.loads(msg))

    async def start_subscription(self, query, variables={}, headers={}):
        sub_id = ''.join(random.choice(
            string.ascii_letters + string.digits) for _ in range(6))
        payload = {
            'type': 'start',
            'id': sub_id,
            'payload': {
                'headers': {},
                'variables': variables,
                'query': query
            }
        }

        await self.ws.send(json.dumps(payload))
        return sub_id

    async def query(self, query, variables={}):
        async with aiohttp.ClientSession(headers={'Authentication': self.access_token}) as session:
            async with session.post(self.http_url, json={'query': query, 'variables': variables}) as resp:
                return await resp.json()

    def stop_subscription(self, sub_id):
        payload = {
            'type': 'stop',
            'id': sub_id
        }
        self.ws.send(json.dumps(payload))

    def close(self):
        self.ws.close()

    # def query(self, query, variables = {}, headers = {}):

class ChatPlugService(ABC):
    def __init__(self, access_token, ws_url, http_url):
        self.ws_url = ws_url
        self.access_token = access_token
        self.http_url = http_url

    async def receive_msg(self, data):
        print(data)
        if data["type"] == "ka":
            return  # keep alive
        
        if data["type"] == "data":
            if data["id"] == self.msg_sub_id:
                msg_packet = data["payload"]["data"]["messageReceived"]
                await self.on_message_received(msg_packet)
            elif data["id"] == self.conf_recv_id:
                cfg = data["payload"]["data"]["configurationReceived"]
                await self.on_configuration_received(cfg)
    
    @abstractmethod
    async def on_message_received(self, msg):
        pass
    
    @abstractmethod
    async def on_configuration_received(self, conf):
        pass

    @abstractmethod
    async def on_connected(self):
        pass

    async def send_message(self, body, origin_id, origin_thread_id, username, author_origin_id, author_avatar_url, attachments):
        resp = await self.ws.query(sendMessageMutation, variables={
            'body': body,
            'originId': origin_id,
            'originThreadId': origin_thread_id,
            'username': username,
            'authorOriginId': author_origin_id,
            'authorAvatarUrl': author_avatar_url,
            'attachments': attachments,
        })
        print(resp)

    async def subscribe_configuration(self, conf_fields):
        self.conf_recv_id = await self.ws.start_subscription(requestConfigurationRequest, variables={'fields': conf_fields})

    async def ws_connected(self):
        self.msg_sub_id = await self.ws.start_subscription(messageReceivedSubscription)
        print(self.msg_sub_id)
        await self.on_connected()

    async def connect(self):
        self.ws = GQLClient(self.ws_url, self.http_url, self.access_token)
        await self.ws.connect(self.ws_connected, self.receive_msg)
