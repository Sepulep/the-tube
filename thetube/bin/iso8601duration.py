import re
from datetime import timedelta

ex="PT3M55S"
  
ISO8601_PERIOD_REGEX = re.compile(r"^(?P<sign>[+-])?"
                r"P(?P<years>[0-9]+([,.][0-9]+)?Y)?"
                r"(?P<months>[0-9]+([,.][0-9]+)?M)?"
                r"(?P<weeks>[0-9]+([,.][0-9]+)?W)?"
                r"(?P<days>[0-9]+([,.][0-9]+)?D)?"
                r"((?P<separator>T)(?P<hours>[0-9]+([,.][0-9]+)?H)?"
                r"(?P<minutes>[0-9]+([,.][0-9]+)?M)?"
                r"(?P<seconds>[0-9]+([,.][0-9]+)?S)?)?$")

def parse_duration(datestring):
    """
    Parses an ISO 8601 durations into datetime.timedelta or Duration objects.
    
    If the ISO date string does not contain years or months, a timedelta instance
    is returned, else a Duration instance is returned.
    
    The following duration formats are supported:
      -PnnW                  duration in weeks
      -PnnYnnMnnDTnnHnnMnnS  complete duration specification
      -PYYYYMMDDThhmmss      basic alternative complete date format
      -PYYYY-MM-DDThh:mm:ss  extended alternative complete date format
      -PYYYYDDDThhmmss       basic alternative ordinal date format
      -PYYYY-DDDThh:mm:ss    extended alternative ordinal date format
      
    The '-' is optional.
      
    Limitations:
      ISO standard defines some restrictions about where to use fractional numbers
      and which component and format combinations are allowed. This parser 
      implementation ignores all those restrictions and returns something when it is
      able to find all necessary components.
      In detail:
        it does not check, whether only the last component has fractions.
        it allows weeks specified with all other combinations
      
      The alternative format does not support durations with years, months or days
      set to 0. 
    """
    if not isinstance(datestring, basestring):
        raise TypeError("Expecting a string %r" % datestring)
    match = ISO8601_PERIOD_REGEX.match(datestring)
    if not match:
        # try alternative format:
        if datestring.startswith("P"):
            durdt = parse_datetime(datestring[1:])
            if durdt.year != 0 or durdt.month != 0:
                # create Duration
                ret = Duration(days=durdt.day, seconds=durdt.second, 
                               microseconds=durdt.microsecond, 
                               minutes=durdt.minute, hours=durdt.hour, 
                               months=durdt.month, years=durdt.year)
            else: # FIXME: currently not possible in alternative format
                # create timedelta
                ret = timedelta(days=durdt.day, seconds=durdt.second, 
                                microseconds=durdt.microsecond,
                                minutes=durdt.minute, hours=durdt.hour)
            return ret
        raise ISO8601Error("Unable to parse duration string %r" % datestring)
    groups = match.groupdict()
    for key, val in groups.items():
        if key not in ('separator', 'sign'):
            if val is None:
                groups[key] = "0n"
            #print groups[key]
            groups[key] = float(groups[key][:-1].replace(',', '.'))
    if groups["years"] == 0 and groups["months"] == 0:
        ret = timedelta(days=groups["days"], hours=groups["hours"],
                        minutes=groups["minutes"], seconds=groups["seconds"],
                        weeks=groups["weeks"])
        if groups["sign"] == '-':
            ret = timedelta(0) - ret
    else: 
        ret = Duration(years=groups["years"], months=groups["months"],
                       days=groups["days"], hours=groups["hours"],
                       minutes=groups["minutes"], seconds=groups["seconds"],
                       weeks=groups["weeks"])
        if groups["sign"] == '-':
            ret = Duration(0) - ret
    return ret


print parse_duration(ex)
