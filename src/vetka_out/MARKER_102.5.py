# MARKER_102.5_START
def test_integration_chat_features():
    """
    Integration test for chat features:
    - Camera functionality
    - Artifact opening
    - Date display
    - Resize handler
    In both solo and team chat modes
    """
    
    # Test solo chat integration
    solo_chat = initialize_solo_chat()
    
    # Camera test
    assert solo_chat.camera.is_functional() == True
    photo = solo_chat.camera.capture()
    assert photo is not None
    
    # Artifact opening test
    artifact = solo_chat.open_artifact("test_artifact_1")
    assert artifact.is_opened() == True
    assert artifact.content_visible() == True
    
    # Date display test
    message_date = solo_chat.get_message_date()
    assert message_date.is_valid() == True
    assert message_date.format_correct() == True
    
    # Resize handler test
    initial_size = solo_chat.get_window_size()
    solo_chat.resize_handler.trigger_resize(width=800, height=600)
    new_size = solo_chat.get_window_size()
    assert new_size != initial_size
    assert solo_chat.ui_elements_proportional() == True
    
    # Test team chat integration
    team_chat = initialize_team_chat()
    
    # Camera test in team context
    assert team_chat.camera.is_functional() == True
    team_photo = team_chat.camera.capture()
    assert team_photo is not None
    assert team_chat.share_media(team_photo) == True
    
    # Artifact opening in team context
    team_artifact = team_chat.open_artifact("team_artifact_1")
    assert team_artifact.is_opened() == True
    assert team_artifact.shared_with_team() == True
    
    # Date display in team context
    team_message_date = team_chat.get_message_date()
    assert team_message_date.is_valid() == True
    assert team_message_date.timezone_consistent() == True
    
    # Resize handler in team context
    team_initial_size = team_chat.get_window_size()
    team_chat.resize_handler.trigger_resize(width=1024, height=768)
    team_new_size = team_chat.get_window_size()
    assert team_new_size != team_initial_size
    assert team_chat.layout_responsive() == True
    
    # Cross-context consistency checks
    assert solo_chat.date_format() == team_chat.date_format()
    assert solo_chat.resize_behavior() == team_chat.resize_behavior()

# MARKER_102.5_END