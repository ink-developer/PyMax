# API Reference

## MaxClient

::: pymax.MaxClient
    handler: python
    selection:
      members:
        - __init__
        - start
        - close
        - send_message
        - edit_message
        - delete_message
        - fetch_history
        - get_user
        - on_message
        - on_start
        - is_connected
        - chats
        - dialogs
        - channels
        - users
        - ws
        - logger

## Типы данных

### Message

::: pymax.Message
    handler: python

### User

::: pymax.User
    handler: python

### Chat

::: pymax.Chat
    handler: python

### Dialog

::: pymax.Dialog
    handler: python

### Channel

::: pymax.Channel
    handler: python

### Element

::: pymax.Element
    handler: python

## Исключения

### InvalidPhoneError

::: pymax.InvalidPhoneError
    handler: python

### WebSocketNotConnectedError

::: pymax.WebSocketNotConnectedError
    handler: python

## Константы

### MessageType

::: pymax.MessageType
    handler: python

### MessageStatus

::: pymax.MessageStatus
    handler: python

### ChatType

::: pymax.ChatType
    handler: python

### AuthType

::: pymax.AuthType
    handler: python

### AccessType

::: pymax.AccessType
    handler: python

### DeviceType

::: pymax.DeviceType
    handler: python

### ElementType

::: pymax.ElementType
    handler: python

### Opcode

::: pymax.Opcode
    handler: python
