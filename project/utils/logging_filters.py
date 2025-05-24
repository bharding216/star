from logging import Filter

class NoEmailLogsFilter(Filter):
    def filter(self, record):
        return not record.getMessage().startswith("send:")

class ExcludeStaticAssets(Filter):
    def filter(self, record):
        return 'GET /static/' not in record.getMessage()