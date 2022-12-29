class SnowfakeMissingConfig(Exception):
    """
    This exception is raised if a new cursor is created without passing in an
    instance of SnowfakeConfig.
    """
    pass


class SnowfakeDuplicateQuery(Exception):
    """
    This exception is raised if `.register()` or `.register_ephemeral()` are used
    to create duplicate queries.
    """
    pass
