class Document:
    def __init__(self, text, metadata=None):
        self.text = text
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Document(text={self.text!r}, metadata={self.metadata!r})"

    def to_dict(self):
        return {
            "text": self.text,
            "metadata": self.metadata
        }
