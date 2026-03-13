from unittest.mock import patch, MagicMock


def test_agent_created_once():
    """_create_agent()가 여러 번 호출되어도 agent를 한 번만 생성하는지 확인"""
    with patch("app.services.agent_service.ChatOpenAI"), \
         patch("app.services.agent_service.create_react_agent") as mock_create, \
         patch("app.services.agent_service.InMemorySaver"):

        mock_create.return_value = MagicMock()

        from app.services.agent_service import AgentService
        service = AgentService()
        service._create_agent()
        service._create_agent()

        mock_create.assert_called_once()


def test_checkpointer_persists():
    """checkpointer가 인스턴스 수명 동안 유지되는지 확인"""
    with patch("app.services.agent_service.ChatOpenAI"), \
         patch("app.services.agent_service.create_react_agent"), \
         patch("app.services.agent_service.InMemorySaver") as mock_saver:

        mock_saver.return_value = MagicMock()

        from app.services.agent_service import AgentService
        service = AgentService()
        service._create_agent()
        service._create_agent()

        mock_saver.assert_called_once()
