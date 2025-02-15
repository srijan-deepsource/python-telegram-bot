#!/usr/bin/env python
#
# A library that provides a Python interface to the Telegram Bot API
# Copyright (C) 2015-2021
# Leandro Toledo de Souza <devs@python-telegram-bot.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.
#
# You should have received a copy of the GNU Lesser Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].
from queue import Queue

import pytest

from telegram import (
    Update,
    Chat,
    Bot,
    ChosenInlineResult,
    User,
    Message,
    CallbackQuery,
    InlineQuery,
    ShippingQuery,
    PreCheckoutQuery,
)
from telegram.ext import ChosenInlineResultHandler, CallbackContext, JobQueue

message = Message(1, None, Chat(1, ''), from_user=User(1, '', False), text='Text')

params = [
    {'message': message},
    {'edited_message': message},
    {'callback_query': CallbackQuery(1, User(1, '', False), 'chat', message=message)},
    {'channel_post': message},
    {'edited_channel_post': message},
    {'inline_query': InlineQuery(1, User(1, '', False), '', '')},
    {'shipping_query': ShippingQuery('id', User(1, '', False), '', None)},
    {'pre_checkout_query': PreCheckoutQuery('id', User(1, '', False), '', 0, '')},
    {'callback_query': CallbackQuery(1, User(1, '', False), 'chat')},
]

ids = (
    'message',
    'edited_message',
    'callback_query',
    'channel_post',
    'edited_channel_post',
    'inline_query',
    'shipping_query',
    'pre_checkout_query',
    'callback_query_without_message',
)


@pytest.fixture(scope='class', params=params, ids=ids)
def false_update(request):
    return Update(update_id=1, **request.param)


@pytest.fixture(scope='class')
def chosen_inline_result():
    return Update(
        1,
        chosen_inline_result=ChosenInlineResult('result_id', User(1, 'test_user', False), 'query'),
    )


class TestChosenInlineResultHandler:
    test_flag = False

    @pytest.fixture(autouse=True)
    def reset(self):
        self.test_flag = False

    def callback_basic(self, bot, update):
        test_bot = isinstance(bot, Bot)
        test_update = isinstance(update, Update)
        self.test_flag = test_bot and test_update

    def callback_data_1(self, bot, update, user_data=None, chat_data=None):
        self.test_flag = (user_data is not None) or (chat_data is not None)

    def callback_data_2(self, bot, update, user_data=None, chat_data=None):
        self.test_flag = (user_data is not None) and (chat_data is not None)

    def callback_queue_1(self, bot, update, job_queue=None, update_queue=None):
        self.test_flag = (job_queue is not None) or (update_queue is not None)

    def callback_queue_2(self, bot, update, job_queue=None, update_queue=None):
        self.test_flag = (job_queue is not None) and (update_queue is not None)

    def callback_context(self, update, context):
        self.test_flag = (
            isinstance(context, CallbackContext)
            and isinstance(context.bot, Bot)
            and isinstance(update, Update)
            and isinstance(context.update_queue, Queue)
            and isinstance(context.job_queue, JobQueue)
            and isinstance(context.user_data, dict)
            and context.chat_data is None
            and isinstance(context.bot_data, dict)
            and isinstance(update.chosen_inline_result, ChosenInlineResult)
        )

    def callback_context_pattern(self, update, context):
        if context.matches[0].groups():
            self.test_flag = context.matches[0].groups() == ('res', '_id')
        if context.matches[0].groupdict():
            self.test_flag = context.matches[0].groupdict() == {'begin': 'res', 'end': '_id'}

    def test_basic(self, dp, chosen_inline_result):
        handler = ChosenInlineResultHandler(self.callback_basic)
        dp.add_handler(handler)

        assert handler.check_update(chosen_inline_result)
        dp.process_update(chosen_inline_result)
        assert self.test_flag

    def test_pass_user_or_chat_data(self, dp, chosen_inline_result):
        handler = ChosenInlineResultHandler(self.callback_data_1, pass_user_data=True)
        dp.add_handler(handler)

        dp.process_update(chosen_inline_result)
        assert self.test_flag

        dp.remove_handler(handler)
        handler = ChosenInlineResultHandler(self.callback_data_1, pass_chat_data=True)
        dp.add_handler(handler)

        self.test_flag = False
        dp.process_update(chosen_inline_result)
        assert self.test_flag

        dp.remove_handler(handler)
        handler = ChosenInlineResultHandler(
            self.callback_data_2, pass_chat_data=True, pass_user_data=True
        )
        dp.add_handler(handler)

        self.test_flag = False
        dp.process_update(chosen_inline_result)
        assert self.test_flag

    def test_pass_job_or_update_queue(self, dp, chosen_inline_result):
        handler = ChosenInlineResultHandler(self.callback_queue_1, pass_job_queue=True)
        dp.add_handler(handler)

        dp.process_update(chosen_inline_result)
        assert self.test_flag

        dp.remove_handler(handler)
        handler = ChosenInlineResultHandler(self.callback_queue_1, pass_update_queue=True)
        dp.add_handler(handler)

        self.test_flag = False
        dp.process_update(chosen_inline_result)
        assert self.test_flag

        dp.remove_handler(handler)
        handler = ChosenInlineResultHandler(
            self.callback_queue_2, pass_job_queue=True, pass_update_queue=True
        )
        dp.add_handler(handler)

        self.test_flag = False
        dp.process_update(chosen_inline_result)
        assert self.test_flag

    def test_other_update_types(self, false_update):
        handler = ChosenInlineResultHandler(self.callback_basic)
        assert not handler.check_update(false_update)

    def test_context(self, cdp, chosen_inline_result):
        handler = ChosenInlineResultHandler(self.callback_context)
        cdp.add_handler(handler)

        cdp.process_update(chosen_inline_result)
        assert self.test_flag

    def test_with_pattern(self, chosen_inline_result):
        handler = ChosenInlineResultHandler(self.callback_basic, pattern='.*ult.*')

        assert handler.check_update(chosen_inline_result)

        chosen_inline_result.chosen_inline_result.result_id = 'nothing here'
        assert not handler.check_update(chosen_inline_result)
        chosen_inline_result.chosen_inline_result.result_id = 'result_id'

    def test_context_pattern(self, cdp, chosen_inline_result):
        handler = ChosenInlineResultHandler(
            self.callback_context_pattern, pattern=r'(?P<begin>.*)ult(?P<end>.*)'
        )
        cdp.add_handler(handler)
        cdp.process_update(chosen_inline_result)
        assert self.test_flag

        cdp.remove_handler(handler)
        handler = ChosenInlineResultHandler(self.callback_context_pattern, pattern=r'(res)ult(.*)')
        cdp.add_handler(handler)

        cdp.process_update(chosen_inline_result)
        assert self.test_flag
