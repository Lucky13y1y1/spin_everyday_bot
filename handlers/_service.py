# SpinEverydayBot
# Copyright © 2016-2017 Evgeniy Filimonov <https://t.me/evgfilim1>
# See full NOTICE at http://github.com/evgfilim1/spin_everyday_bot

from logging import DEBUG

import data
import utils
import config
from ._help import start_help_handler

log = utils.set_up_logger(__name__, DEBUG)


def handle_error(bot, update, error):
    log.error(f'Update {update} caused error: {error}')
    if config.SHOW_ERRORS:
        update.effective_message.reply_text(utils.get_lang(update.effective_chat.id, 'error'))


def update_cache(bot, update):
    user = update.effective_user
    chat_id = update.effective_message.chat_id
    # Also skip first update when the bot is added
    if not utils.is_private(chat_id) and data.chat_users.get(chat_id) is not None:
        if user.id not in data.chat_users[chat_id]:
            data.chat_users[chat_id].append(user.id)
        if user.name != data.usernames.get(user.id):
            data.usernames.update({user.id: user.name})


def svc_handler(bot, update):
    chat_id = update.message.chat_id
    migrate_to_id = update.message.migrate_to_chat_id
    new_members = update.message.new_chat_members
    left_member = update.message.left_chat_member
    if update.message.group_chat_created or \
            (len(new_members) != 0 and any(new_member.id == bot.id for new_member in new_members)):
        # TODO: add admins to the list
        log.info(f'New chat! ({chat_id})')
        data.chat_users[chat_id] = []
        data.can_change_name[chat_id] = []
        start_help_handler(bot, update, [])
    elif new_members:
        for new_member in new_members:
            if new_member.is_bot:
                return
            if new_member.id not in data.chat_users[chat_id]:
                data.chat_users[chat_id].append(new_member.id)
            data.usernames.update({new_member.id: new_member.name})
    elif migrate_to_id:
        data.migrate(chat_id, migrate_to_id)
    elif left_member and left_member.id == bot.id:
        data.clear_chat_data(chat_id)
    elif left_member:
        if left_member.is_bot:
            return
        try:
            data.chat_users[chat_id].pop(data.chat_users[chat_id].index(left_member.id))
        except KeyError:
            # Passing this because of unknown users
            pass