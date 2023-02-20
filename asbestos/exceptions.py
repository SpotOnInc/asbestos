class AsbestosMissingConfig(Exception):
    """
    This exception is raised if a new cursor is created without passing in an
    instance of AsbestosConfig.
    """

    pass


class AsbestosDuplicateQuery(Exception):
    """
    This exception is raised if `.register()` or `.register_ephemeral()` are used
    to create duplicate queries.
    """

    pass
