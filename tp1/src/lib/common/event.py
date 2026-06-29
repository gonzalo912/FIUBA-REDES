class Event:
    def __init__(self, event_type, **args):
        self.type = event_type
        self.__dict__.update(args)