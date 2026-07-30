class UnsupportedFeature(Exception):
    """Raised when Python source uses a construct py2bs cannot translate."""

    def __init__(self, feature, line=None, detail=None):
        self.feature = feature
        self.line = line
        self.detail = detail
        message = feature
        if detail:
            message = f'{feature}: {detail}'
        if line:
            message = f'line {line}: {message}'
        super().__init__(message)
