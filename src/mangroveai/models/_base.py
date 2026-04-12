from pydantic import BaseModel, ConfigDict


class MangroveModel(BaseModel):
    """Base model for all SDK types.

    Configured to accept unknown fields from the server without
    raising validation errors, ensuring forward compatibility.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)
