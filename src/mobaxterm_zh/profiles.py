"""Migrate only built-in tree-root prefixes in two history-reference sections.

All other bytes, including bookmark definitions, credentials, custom names and
connection settings, are preserved. Use a new profile and retain the source.
"""
def migrate(data):
    current = b''
    changes = []
    result = []
    old = b'User sessions\\'
    new = '用户会话\\'.encode('gbk')
    for line in data.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith(b'[') and stripped.endswith(b']'):
            current = stripped[1:-1].lower()
        if current in (b'recently started', b'lastinstancesessions'):
            key, equals, value = line.partition(b'=')
            if equals and key.strip().isdigit():
                padding = len(value)-len(value.lstrip(b' \t'))
                if value[padding:].startswith(old):
                    replaced = value[:padding]+new+value[padding+len(old):]
                    line = key+equals+replaced
                    changes.append({'section':current.decode('ascii'),'key':key.strip().decode('ascii'),
                                    'old_root':'User sessions','new_root':'用户会话'})
        result.append(line)
    return b''.join(result),changes
