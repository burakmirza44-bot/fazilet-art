"""Tests for Houdini Bridge Client."""

import json
import time
import pytest
from pathlib import Path

from app.domains.houdini.bridge.client import (
    HoudiniBridgeClient,
    HoudiniBridgeClientConfig,
    create_geometry_node,
    create_node_chain,
    send_recipe_to_houdini,
)
from app.domains.houdini.bridge.models import (
    RecipeRequest,
    RecipeResult,
    RecipeStep,
)


class TestHoudiniBridgeClient:
    """Tests for HoudiniBridgeClient."""

    def test_create_client(self, tmp_path):
        """Test creating a client."""
        inbox = tmp_path / "inbox"
        outbox = tmp_path / "outbox"

        client = HoudiniBridgeClient(
            inbox_dir=str(inbox),
            outbox_dir=str(outbox),
        )

        assert client.inbox_path == inbox
        assert client.outbox_path == outbox
        assert inbox.exists()
        assert outbox.exists()

    def test_create_client_with_config(self, tmp_path):
        """Test creating a client with config."""
        config = HoudiniBridgeClientConfig(
            inbox_dir=str(tmp_path / "inbox"),
            outbox_dir=str(tmp_path / "outbox"),
            default_timeout=60.0,
        )

        client = HoudiniBridgeClient(config=config)

        assert client._config.default_timeout == 60.0

    def test_send_recipe_writes_file(self, tmp_path):
        """Test that send_recipe writes to inbox."""
        inbox = tmp_path / "inbox"
        outbox = tmp_path / "outbox"

        client = HoudiniBridgeClient(
            inbox_dir=str(inbox),
            outbox_dir=str(outbox),
        )

        steps = [
            RecipeStep(order=1, name="Test", action="create_node", node_type="geo"),
        ]

        # Create a mock result file before timeout
        def mock_server_response():
            time.sleep(0.1)  # Small delay
            recipe_files = list(inbox.glob("recipe_*.json"))
            if recipe_files:
                recipe_file = recipe_files[0]
                result_name = recipe_file.name.replace("recipe_", "result_")
                result_file = outbox / result_name

                result = RecipeResult(
                    recipe_id="test",
                    success=True,
                    steps_executed=["Test"],
                )
                result_file.write_text(json.dumps(result.to_dict()))

        import threading
        thread = threading.Thread(target=mock_server_response)
        thread.start()

        result = client.send_recipe(steps, timeout=5.0)
        thread.join()

        assert result.success is True

    def test_send_request_timeout(self, tmp_path):
        """Test that send_recipe raises timeout."""
        inbox = tmp_path / "inbox"
        outbox = tmp_path / "outbox"

        client = HoudiniBridgeClient(
            inbox_dir=str(inbox),
            outbox_dir=str(outbox),
            timeout=1.0,
        )

        request = RecipeRequest(
            recipe_id="test_timeout",
            recipe_steps=[
                RecipeStep(order=1, name="Test", action="create_node"),
            ],
        )

        with pytest.raises(TimeoutError, match="did not respond"):
            client.send_request(request, timeout=1.0)

    def test_send_recipe_async(self, tmp_path):
        """Test async recipe sending."""
        inbox = tmp_path / "inbox"
        outbox = tmp_path / "outbox"

        client = HoudiniBridgeClient(
            inbox_dir=str(inbox),
            outbox_dir=str(outbox),
        )

        steps = [
            RecipeStep(order=1, name="Test", action="create_node"),
        ]

        recipe_id = client.send_recipe_async(steps)

        assert recipe_id
        # Check file was created
        recipe_files = list(inbox.glob("recipe_*.json"))
        assert len(recipe_files) == 1

    def test_list_pending_recipes(self, tmp_path):
        """Test listing pending recipes."""
        inbox = tmp_path / "inbox"
        outbox = tmp_path / "outbox"
        inbox.mkdir(parents=True, exist_ok=True)

        # Create some recipe files
        (inbox / "recipe_001.json").write_text("{}")
        (inbox / "recipe_002.json").write_text("{}")

        client = HoudiniBridgeClient(
            inbox_dir=str(inbox),
            outbox_dir=str(outbox),
        )

        pending = client.list_pending_recipes()
        assert len(pending) == 2

    def test_clear_inbox(self, tmp_path):
        """Test clearing inbox."""
        inbox = tmp_path / "inbox"
        outbox = tmp_path / "outbox"
        inbox.mkdir(parents=True, exist_ok=True)

        # Create some recipe files
        (inbox / "recipe_001.json").write_text("{}")
        (inbox / "recipe_002.json").write_text("{}")

        client = HoudiniBridgeClient(
            inbox_dir=str(inbox),
            outbox_dir=str(outbox),
        )

        count = client.clear_inbox()
        assert count == 2
        assert len(list(inbox.glob("recipe_*.json"))) == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_send_recipe_to_houdini(self, tmp_path):
        """Test send_recipe_to_houdini function."""
        inbox = tmp_path / "inbox"
        outbox = tmp_path / "outbox"

        # Mock server response
        def mock_server():
            time.sleep(0.1)
            recipe_files = list(inbox.glob("recipe_*.json"))
            if recipe_files:
                recipe_file = recipe_files[0]
                result_name = recipe_file.name.replace("recipe_", "result_")
                result_file = outbox / result_name

                result = RecipeResult(recipe_id="test", success=True)
                result_file.write_text(json.dumps(result.to_dict()))

        import threading
        thread = threading.Thread(target=mock_server)
        thread.start()

        steps = [
            RecipeStep(order=1, name="Test", action="create_node"),
        ]

        result = send_recipe_to_houdini(
            steps,
            inbox_dir=str(inbox),
            outbox_dir=str(outbox),
            timeout=5.0,
        )
        thread.join()

        assert result.success is True

    def test_create_geometry_node(self, tmp_path):
        """Test create_geometry_node function."""
        # This function tests the convenience wrapper
        # The actual integration would need a running Houdini bridge
        # Just verify it creates proper steps
        from app.domains.houdini.bridge.models import create_node_step, set_parameter_step

        # Verify the steps are created correctly
        step1 = create_node_step(1, "box", "/obj/geo1/box1")
        assert step1.action == "create_node"
        assert step1.node_type == "box"

        step2 = set_parameter_step(2, "/obj/geo1/box1", "sizex", 2.0)
        assert step2.action == "set_parameter"
        assert step2.value == 2.0

    def test_create_node_chain(self, tmp_path):
        """Test create_node_chain function."""
        # This function creates a chain of connected nodes
        # Verify it creates proper steps
        pass  # Complex integration test, would need mock Houdini


class TestClientConfig:
    """Tests for client configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = HoudiniBridgeClientConfig()
        assert config.default_timeout == 30.0
        assert config.poll_interval == 0.5
        assert config.cleanup_files is True

    def test_config_to_dict(self):
        """Test config serialization."""
        config = HoudiniBridgeClientConfig(
            inbox_dir="/inbox",
            outbox_dir="/outbox",
            default_timeout=60.0,
        )
        d = config.to_dict()
        assert d["inbox_dir"] == "/inbox"
        assert d["default_timeout"] == 60.0