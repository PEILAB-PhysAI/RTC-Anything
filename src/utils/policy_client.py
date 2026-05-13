"""Policy client adapter used by deployment entrypoints.

Customize this file when replacing the default OpenPI-compatible websocket
backend with another model server or local inference runtime.
"""

class PolicyClient:
    """Thin adapter around the policy backend used by RTC Anything."""

    def __init__(self, host="localhost", port=8000):
        from openpi_client import image_tools
        from openpi_client import websocket_client_policy

        self.backend = websocket_client_policy.WebsocketClientPolicy(host, port)
        self.image_tools = image_tools
        self.observation = None

    def process_image(self, image):
        """Resize and convert an RGB image to the policy input layout."""
        return self.image_tools.convert_to_uint8(
            self.image_tools.resize_with_pad(image, 224, 224).transpose(2, 0, 1)
        )

    def update_observation(self, obs):
        """Preprocess raw images and store the latest observation."""
        processed_obs = dict(obs)
        processed_obs["images"] = {
            name: self.process_image(image)
            for name, image in obs.get("images", {}).items()
            if image is not None
        }
        self.observation = processed_obs

    def get_action(self):
        """Return an action chunk for the latest observation."""
        if self.observation is None:
            raise RuntimeError("Policy observation is empty. Call update_observation(obs) before get_action().")
        return self.backend.infer(self.observation)["actions"]

    def reset(self):
        """Reset backend episode state if the policy requires it.

        OpenPI pi0 does not require per-episode reset, so the default adapter is
        intentionally a no-op. Override this method for stateful policy backends.
        """
        return None
