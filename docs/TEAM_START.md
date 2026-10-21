# Team responsibilities and viva reading guide

This is the current implementation guide. Start the server with `python run_server.py` and each desktop client with `python run.py` using the setup in the root readme. There are no demo clients or placeholder components.

| Member | Main responsibility | Reading order |
|---|---|---|
| Ammar-Bin-Yasir | UI, integration, storage, discovery and media | run.py, client/ui/, client/network/, client/media/, shared/protocol.py, server/storage/, server/services/auth.py and calls.py |
| Hafiz Muhammad Abdullah Aamir | Connections and presence | run_server.py, server/transport/listener.py, connection.py and registry.py |
| Ashna-Simi-Butt | Private/group text and access rules | server/services/messaging.py and groups.py; server/storage/conversations.py with Ammar |
| Ayesha Zulqarnain | File transfers | client/network/files.py, server/services/files.py; server/storage/attachments.py with Ammar |

For the profile feature, Ammar should also read client/ui/profiles.py and server/storage/profiles.py. The GUI prepares the picture and sends a request; the authenticated connection determines ownership; the existing database worker persists it and a refresh event updates other clients.

Each member should trace a successful request and a rejected request, identify which thread executes each step, and explain sender/session authorization. Database records persist; socket connections and session tokens do not. A saved acknowledgement is not a read receipt.

## Demonstration

Use four separate accounts and ideally four laptops; one laptop may run both server and client. Show online presence, private text including an offline recipient, protected group join/rejection, a file download, a recorded voice message, and accepted/rejected/ended calls. Two independent pairs may call at once. Use headphones.

Local socket, Qt and device checks are recorded outside Git. They do not establish audible quality or Windows behaviour on the demonstration laptops. Rehearse with those devices and retain the runtime directory to demonstrate persistence.
