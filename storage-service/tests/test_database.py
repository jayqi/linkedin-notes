from pydantic import TypeAdapter

from linkedin_notes_storage.database import Profile


def test_profile_validation():
    adapter = TypeAdapter(Profile)

    assert adapter.validate_python("in/username/") == "in/username/"
    assert adapter.validate_python("/in/username/") == "in/username/"
    assert adapter.validate_python("in/username") == "in/username/"
    assert adapter.validate_python("username") == "in/username/"
    assert adapter.validate_python("https://www.linkedin.com/in/username/") == "in/username/"
    assert adapter.validate_python("http://www.linkedin.com/in/username/") == "in/username/"
    assert adapter.validate_python("https://www.linkedin.com/in/username") == "in/username/"
    assert adapter.validate_python("https://linkedin.com/in/username/") == "in/username/"
