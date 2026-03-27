"""
Decorators for Matrix Bob command functions.

This module provides decorators that add functionality to command methods,
such as automatic docopt parsing and permission checks.
"""

import functools
from docopt import docopt, DocoptExit


def matrix_command(func):
    """
    Decorator that adds automatic docopt parsing to command methods.
    
    The decorated function's docstring should follow docopt format.
    If parsing fails, sends the docstring as help text to the user.
    
    Args:
        func: The command function to decorate
    
    Returns:
        Wrapped function with docopt parsing
    
    Example:
        @matrix_command
        async def _mycommand(self, opts, matrix_room, event):
            '''
            My command description.
            
            Usage:
              mycommand [--option]
            '''
            if opts['--option']:
                # do something
                pass
    """
    @functools.wraps(func)
    async def fn(self, args, matrix_room, event):
        # Import here to avoid circular imports
        from pawnai_bob.utils.chat import send_text_to_room
        from pawnai_bob import client
        
        try:
            opts = docopt(fn.__doc__, args)
        except DocoptExit as e:
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                fn.__doc__,
                notice=True,
                event=event
            )
            return True

        return await func(self, opts, matrix_room, event)

    return fn


def power_user_function(func):
    """
    Decorator that restricts command execution to power users only.
    
    Power users are defined in the configuration settings.
    If a non-power user tries to execute the command, they receive
    an error message.
    
    Args:
        func: The command function to decorate
    
    Returns:
        Wrapped function with power user check
    
    Example:
        @power_user_function
        @matrix_command
        async def _admin_command(self, opts, matrix_room, event):
            '''
            Admin-only command.
            
            Usage:
              admin_command
            '''
            # Only power users can execute this
            pass
    """
    @functools.wraps(func)
    async def fn(self, args, matrix_room, event):
        # Import here to avoid circular imports
        from pawnai_bob.utils.chat import send_text_to_room
        from pawnai_bob import client, settings
        
        if event.sender not in settings().power_users:
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                "This function requires power user rights!",
                notice=True,
                event=event
            )
            return True

        return await func(self, args, matrix_room, event)

    return fn
