import time

class TemplateFilters:

    @staticmethod
    def secToStrfTime(s):
        return time.strftime('%m/%d, %I:%M%p', time.localtime(s))

    @staticmethod
    def secToDay(s):
        return time.strftime('%A %m/%d', time.localtime(s))

    @staticmethod
    def degrees_to_cardinal(d):
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE",
                "SE", "SSE", "S", "SSW", "SW", "WSW",
                "W", "WNW", "NW", "NNW"]
        ix = int((d + 11.25) / 22.5 - 0.02)
        return dirs[ix % 16]

    @staticmethod
    def register_template_filters_to_env(env):
        env.filters['secToStrfTime'] = TemplateFilters.secToStrfTime
        env.filters['toCardinal'] = TemplateFilters.degrees_to_cardinal
        env.filters['secToDay'] = TemplateFilters.secToDay
