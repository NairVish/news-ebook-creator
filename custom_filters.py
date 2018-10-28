import time


class TemplateFilters:
    """
    Some filters that the html templates use.
    """

    @staticmethod
    def secToStrfTime(s):
        """
        Converts the current time in seconds into a readable datetime.
        :param s: The current time in seconds.
        :return: The readable datetime.
        """
        return time.strftime('%m/%d, %I:%M%p', time.localtime(s))

    @staticmethod
    def secToDay(s):
        """
        Converts the current time in seconds into a readable date.
        :param s: The current time in seconds.
        :return: The readable date.
        """
        return time.strftime('%A %m/%d', time.localtime(s))

    @staticmethod
    def degrees_to_cardinal(d):
        """
        Converts a bearing in degrees into cardinal directions. A highly approximate conversion.
        :param d: The bearing in degrees.
        :return: The converted cardinal direction.
        """
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE",
                "SE", "SSE", "S", "SSW", "SW", "WSW",
                "W", "WNW", "NW", "NNW"]
        ix = int((d + 11.25) / 22.5 - 0.02)
        return dirs[ix % 16]

    @staticmethod
    def register_template_filters_to_env(env):
        """
        Registers the above functions as template filters.
        :param env: The already-instantiated Jinja2 environment.
        """
        env.filters['secToStrfTime'] = TemplateFilters.secToStrfTime
        env.filters['toCardinal'] = TemplateFilters.degrees_to_cardinal
        env.filters['secToDay'] = TemplateFilters.secToDay
