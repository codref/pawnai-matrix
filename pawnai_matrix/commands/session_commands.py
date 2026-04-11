import re

from pawnai_bob.utils import send_text_to_room
from pawnai_bob.utils.decorators import matrix_command
from pawnai_bob import client, room


class SessionCommands:
    _ALIAS_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")

    @staticmethod
    def _validate_alias(alias: str) -> bool:
        return bool(SessionCommands._ALIAS_PATTERN.match(alias))

    @matrix_command
    async def _session(self, opts, matrix_room, event):
        """
        Usage:
          session current
          session ls
          session new <name>
          session use <name>
          session reset
        """

        if "current" in opts and opts["current"]:
            alias = room().get_current_session_alias(matrix_room)
            session_id = room().get_current_session_id(matrix_room)
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"Current session: `{alias}`\nSession ID: `{session_id}`",
                notice=True,
                event=event,
            )
            return True

        if "ls" in opts and opts["ls"]:
            sessions = room().get_sessions(matrix_room)
            current = room().get_current_session_alias(matrix_room)

            default_alias = room().DEFAULT_SESSION_ALIAS
            aliases = []
            if default_alias in sessions:
                aliases.append(default_alias)
            aliases.extend(alias for alias in sorted(sessions.keys()) if alias != default_alias)
            lines = ["Sessions:"]
            for alias in aliases:
                marker = " (current)" if alias == current else ""
                lines.append(f"- `{alias}` -> `{sessions[alias]}`{marker}")

            await send_text_to_room(
                client(),
                matrix_room.room_id,
                "\n".join(lines),
                notice=True,
                event=event,
            )
            return True

        if "new" in opts and opts["new"]:
            alias = opts["<name>"]
            if not self._validate_alias(alias):
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    "Invalid session name. Use 1-32 chars: lowercase letters, digits, `_`, `-`.",
                    notice=True,
                    event=event,
                )
                return True

            try:
                session_id = room().create_session(matrix_room, alias)
            except ValueError as exc:
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    str(exc),
                    notice=True,
                    event=event,
                )
                return True

            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"Session `{alias}` created and activated.\nSession ID: `{session_id}`",
                notice=True,
                event=event,
            )
            return True

        if "use" in opts and opts["use"]:
            alias = opts["<name>"]
            if not self._validate_alias(alias):
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    "Invalid session name. Use 1-32 chars: lowercase letters, digits, `_`, `-`.",
                    notice=True,
                    event=event,
                )
                return True

            try:
                session_id = room().use_session(matrix_room, alias)
            except ValueError as exc:
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    str(exc),
                    notice=True,
                    event=event,
                )
                return True

            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"Session switched to `{alias}`.\nSession ID: `{session_id}`",
                notice=True,
                event=event,
            )
            return True

        if "reset" in opts and opts["reset"]:
            alias = room().get_current_session_alias(matrix_room)
            room().get_client(matrix_room).reset_chat_engine()
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"Session `{alias}` has been reset.",
                notice=True,
                event=event,
            )
            return True

        return True
