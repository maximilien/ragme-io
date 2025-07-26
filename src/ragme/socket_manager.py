# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Socket manager for emitting events from the API to connected frontend clients.
"""

import socketio

# Global socket manager instance
_sio: socketio.AsyncServer | None = None


def set_socket_manager(sio: socketio.AsyncServer):
    """Set the global socket manager instance."""
    global _sio
    _sio = sio


def emit_document_added(doc_type: str, count: int):
    """
    Emit a document added event to all connected clients.

    Args:
        doc_type: Type of document added ("urls" or "json")
        count: Number of documents added
    """
    global _sio
    if _sio is not None:
        try:
            # Emit to all connected clients
            _sio.emit(
                "document_added",
                {
                    "type": doc_type,
                    "count": count,
                    "message": f"Added {count} {doc_type} document(s)",
                },
            )
        except Exception as e:
            # Log error but don't fail the API call
            print(f"Failed to emit socket event: {e}")
