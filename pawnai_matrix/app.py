import os
import asyncio
import nest_asyncio
import datetime
import logging
from time import sleep
from aiohttp import ClientConnectionError, ServerDisconnectedError
from nio import (
    InviteMemberEvent,
    LocalProtocolError,
    LoginError,
    MegolmEvent,
    RoomMessageText,
    RoomMessageFile,
    RoomEncryptedFile,
    RoomMessageImage,
    RoomEncryptedImage,
    RoomMessageAudio,
    RoomEncryptedAudio,
    UnknownEvent,
)

from pawnai_bob.callbacks import Callbacks
from pawnai_bob import client, init, config, set_started_on
from pawnai_bob.settings import resolve_config_path

log = logging.getLogger(__name__)

class App():

    async def main_worker(self):
        """
        Infinite loop to process messages coming from Matrix server
        """

        set_started_on(datetime.datetime.now())

        if config().get('matrix.user_token'):
            client().access_token = config().get('matrix.user_token')
            client().user_id = config().get('matrix.user_id')

        # Set up event callbacks
        callbacks = Callbacks()
        client().add_event_callback(callbacks.message, (RoomMessageText,))
        client().add_event_callback(callbacks.uploaded_file, (RoomMessageAudio, RoomEncryptedAudio))
        client().add_event_callback(callbacks.uploaded_file, (RoomMessageFile, RoomEncryptedFile))
        client().add_event_callback(callbacks.uploaded_file, (RoomMessageImage, RoomEncryptedImage))
        client().add_event_callback(
            callbacks.invite_event_filtered_callback, (InviteMemberEvent,)
        )
        client().add_event_callback(callbacks.decryption_failure, (MegolmEvent,))
        client().add_event_callback(callbacks.unknown, (UnknownEvent,))

        # Keep trying to reconnect on failure (with some time in-between)
        while True:
            try:
                if config().get('matrix.user_token'):
                    # Use token to log in
                    client().load_store()

                    # Sync encryption keys with the server
                    if client().should_upload_keys:
                        await client().keys_upload()
                else:
                    # Try to login with the configured username/password
                    try:
                        login_response = await client().login(
                            password=config().get('matrix.user_password'),
                            device_name=config().get('matrix.device_name'),
                        )

                        # Check if login failed
                        if type(login_response) == LoginError:
                            log.error("Failed to login: %s", login_response.message)
                            return False
                    except LocalProtocolError as e:
                        # There's an edge case here where the user hasn't installed the correct C
                        # dependencies. In that case, a LocalProtocolError is raised on login.
                        log.fatal(
                            "Failed to login. Have you installed the correct dependencies? "
                            "https://github.com/poljar/matrix-nio#installation "
                            "Error: %s",
                            e,
                        )
                        return False

                    # Login succeeded!

                log.info(f"Logged in as {config().get('matrix.user_id')}")
                await client().sync_forever(timeout=60000, full_state=True)

            except (ClientConnectionError, ServerDisconnectedError):
                log.warning("Unable to connect to homeserver, retrying in 15s...")

                # Sleep so we don't bombard the server with login requests
                sleep(15)
            except asyncio.TimeoutError:
                # Syncing with the homeserver may time out occasionally if:
                #   1. There are no new events to sync in the timeout period.
                #   2. The server is taking a long time to respond to the request
                #  In both of these cases, let's just try again.
                log.debug("Timed out while syncing with homeserver.")            
            finally:
                # Make sure to close the client connection on disconnect
                await client().close()

    def main_loop(self, config_file_path=None):
        '''
        Main loop implemented through asynchronous task.
        '''
        # Run the main function in an asyncio event loop
        nest_asyncio.apply()

        # Initialize Globals
        if config_file_path is None:
            config_file_path = str(resolve_config_path())

        init(config_file_path)

        loop = asyncio.get_event_loop()

        try:
            asyncio.ensure_future(self.main_worker())  
            print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
            loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            # TODO better catch exceptions at termination
            # https://quantlane.com/blog/ensure-asyncio-task-exceptions-get-logged/
            pass
        finally:
            logging.info("Terminating...")
            loop.close()                

        logging.info('Shutting down')
