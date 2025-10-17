import random


class Navigation:
    SCREENS_GRAPH = {  # noqa: RUF012
        "chats_list_tab": [
            "chat",
            "contacts_tab",
            "call_history_tab",
            "settings_tab",
            "create_chat",
            "chat_attachments_voices",
        ],
        "chat": [
            "chats_list_tab",
            "chat_attachments_media",
        ],
        "contacts_tab": [
            "call_history_tab",
            "chats_list_tab",
            "settings_tab",
            "create_chat",
        ],
        "call_history_tab": [
            "chats_list_tab",
            "settings_tab",
            "contacts_tab",
        ],
        "settings_tab": [
            "settings_folders",
            "settings_privacy",
            "settings_notifications",
            "settings_chat_decoration",
            "call_history_tab",
            "contacts_tab",
            "chats_list_tab",
        ],
        "settings_folders": [
            "settings_tab",
            "chats_list_tab",
            "contacts_tab",
            "call_history_tab",
        ],
        "settings_privacy": [
            "settings_tab",
            "chats_list_tab",
            "contacts_tab",
            "call_history_tab",
        ],
        "settings_notifications": [
            "settings_tab",
            "contacts_tab",
            "call_history_tab",
            "chats_list_tab",
        ],
        "settings_chat_decoration": [
            "settings_tab",
            "chats_list_tab",
            "contacts_tab",
            "call_history_tab",
        ],
        "create_chat": [
            "chats_list_tab",
            "contacts_tab",
        ],
        "chat_attachments_media": [
            "chat_attachments_files",
            "chat_attachments_voices",
            "chat_attachments_links",
            "chat",
        ],
        "chat_attachments_files": [
            "chat_attachments_voices",
            "chat_attachments_media",
            "chat_attachments_links",
            "chat",
        ],
        "chat_attachments_voices": [
            "chat_attachments_links",
            "chat_attachments_media",
            "chat_attachments_files",
            "chat",
        ],
        "chat_attachments_links": [
            "chat_attachments_media",
            "chat_attachments_files",
            "chat_attachments_voices",
            "chat",
        ],
    }
    SCREENS = {  # noqa: RUF012
        "application_background": 1,
        "auth_sign_method": 50,
        "auth_phone_login": 51,
        "auth_otp": 52,
        "auth_empty_profile": 53,
        "auth_avatars": 54,
        "contacts_tab": 100,
        "contacts_search": 102,
        "contacts_search_by_phone": 103,
        "chats_list_tab": 150,
        "chats_list_search_initial": 151,
        "chats_list_search_result": 152,
        "create_chat": 200,
        "create_chat_members_picker": 201,
        "create_chat_info": 202,
        "avatar_picker_gallery": 250,
        "avatar_picker_crop": 251,
        "avatar_picker_camera": 252,
        "avatar_viewer": 253,
        "call_history_tab": 300,
        "call_new_call": 302,
        "call_create_group_link": 303,
        "call_add_participants": 304,
        "call": 305,
        "chat": 350,
        "chat_attach_picker": 351,
        "chat_attach_picker_media_viewer": 352,
        "chat_attach_picker_camera": 353,
        "chat_share_location": 354,
        "chat_share_contact": 355,
        "chat_forward": 357,
        "chat_media_viewer": 358,
        "chat_system_file_viewer": 359,
        "chat_location_viewer": 360,
        "chat_info": 400,
        "chat_info_all_participants": 401,
        "chat_info_editing": 402,
        "chat_info_add_participants": 403,
        "chat_info_administrators": 404,
        "chat_info_add_administrator": 405,
        "chat_info_blocked_participants": 406,
        "chat_info_change_owner": 407,
        "chat_attachments_media": 408,
        "chat_attachments_files": 409,
        "chat_attachments_links": 410,
        "chat_info_invite_link": 411,
        "chat_attachments_voices": 412,
        "settings_tab": 450,
        "settings_profile_editing": 451,
        "settings_shortname_change": 452,
        "settings_phone_change": 453,
        "settings_notifications": 454,
        "settings_notifications_system": 455,
        "settings_folders": 456,
        "settings_privacy": 457,
        "settings_privacy_block_list": 458,
        "settings_media": 459,
        "settings_messages": 460,
        "settings_stickers": 461,
        "settings_chat_decoration": 462,
        "settings_phone_change_phone_input": 463,
        "settings_phone_change_phone_otp": 464,
        "settings_cache": 465,
        "settings_profile_avatars": 466,
        "settings_about_application": 467,
        "settings_privacy_sensitive_content": 479,
        "miniapp": 500,
    }

    @classmethod
    def get_screen_id(cls, screen_name: str) -> int:
        screen_id = cls.SCREENS.get(screen_name)

        if screen_id is None:
            raise ValueError(f"Unknown screen name: {screen_name}")

        return screen_id

    @classmethod
    def can_navigate(cls, from_screen: str, to_screen: str) -> bool:
        if from_screen == to_screen:
            return True
        return to_screen in cls.SCREENS_GRAPH.get(from_screen, [])

    @classmethod
    def get_random_navigation(cls, screen_name: str) -> str:
        return random.choice(  # nosec B311
            cls.SCREENS_GRAPH.get(screen_name, [])
        )

    @classmethod
    def get_screen_name(cls, screen_id: int) -> str | None:
        for name, id_ in cls.SCREENS.items():
            if id_ == screen_id:
                return name
        return None
