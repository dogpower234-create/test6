"""
Field-description constants and field names shared by states and
counties. The field-description constants are copied from
backendcore/data/fields.py, so this project does not depend on it.
"""

BAR = 'bar'
CHECKBOX = 'checkbox'
CHOICES = 'choices'
CLICK = 'click'
DEC_PLACES = 'decimalPlaces'
DESCR = 'description'
DICT = 'dict'
DISP_NAME = 'name'
DSRC_LINK = 'datasources'
FLD_TYPE = 'type'
FLOAT = 'float'
GRAPH = 'graph'
HIDDEN = 'hidden'
HI_VAL = 'high_value'
HOVER = 'hover'
INT = 'int'
JUSTIFICATION = 'justification'
LEFT = 'start'
LINE = 'line'
LINK = 'link'
LINK_ACTIVATE = 'link-activate'
LINK_TYPE = 'link-type'
LIST = 'list'
LOW_VAL = 'low_value'
MAP = 'map'
MARKDOWN = 'markdown'  # field contains markdown
MAX_LEN = 'maxLen'
ORIGIN = '$ORIGIN'
# sometimes we don't want sorting on a field; set this to True:
NO_SORT = 'noSort'
RIGHT = 'end'
STR = 'string'
VAL = '$VAL'
WIDTH = 'width'

# Common field names:
CODE = 'code'
DATE = 'date'
MORE_INFO = 'more_info'
MORE_INFO_DISP_NM = 'More info'
NAME = 'name'

# Field values:
DATE_LEN = 10
STATE_CODE_LEN = 2

# Field names shared by states and counties:
STATE_CODE = 'state_code'
POPULATION = 'population'
AREA = 'area'
