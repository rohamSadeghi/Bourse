from urllib.parse import parse_qsl
from django.core.cache import cache
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class FilterConsumer(AsyncJsonWebsocketConsumer):

    async def websocket_connect(self, event):
        try:
            query_string = self.scope['query_string'].decode('utf-8')
            query_params = dict(parse_qsl(query_string))
            ticket_uuid = query_params.get('ticket_uuid')
            self.scope['has_ticket'] = cache.get(ticket_uuid)
            if not cache.delete(ticket_uuid):
                raise Exception('ticket not found')
        except:
            await self.close()
            return

        await self.channel_layer.group_add(
            'free_signals',
            self.channel_name
        )

        if self.scope['has_ticket']:
            await self.channel_layer.group_add(
                'filter_signals',
                self.channel_name
            )

        await self.accept()

    async def free_signals_message(self, event):
        await self.send_json(event["content"])

    async def filter_signals_message(self, event):
        await self.send_json(event["content"])

    async def websocket_disconnect(self, event):
        await self.channel_layer.group_discard(
            'free_signals',
            self.channel_name
        )

        if self.scope.get('has_ticket'):
            await self.channel_layer.group_discard(
                'filter_signals',
                self.channel_name
            )
