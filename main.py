from os.path import exists

import keyboard
from pywinauto.application import Application


path_to_config = 'config.txt'
hooks = []
cur_toggle = None
shift_sc = (42, 54)
numpad_prefix = 'VK_NUMPAD'
mod_start_char = '['
mod_end_char = ']'
comment_start_char = '//'
mods_vk = []
mods_sc = []
keys_vk = []
keys_sc = []
alts_vk = {}
alts_sc = {}
win = None
main_app_title = 'PCSX2  1.6.0'
main_win_title = 'WM Keyboard'
main_win_class = 'SysListView32'
game_app_title = 'Slot:*'
game_win_title = 'Slot:*'


def parse_config(config):
    global mods_vk, mods_sc, keys_vk, keys_sc, alts_vk, alts_sc
    for line in config.readlines():
        sc_index = 0
        # skip comments
        if line.startswith(comment_start_char):
            continue
        line = line.strip()
        if not line:
            continue
        # parse mod
        if line.startswith(mod_start_char) and line.endswith(mod_end_char):
            mod = line.strip(mod_start_char + mod_end_char)
            mods_vk.append(mod)
            mods_sc.append(keyboard.key_to_scan_codes(mod)[sc_index])
            alts_vk[mods_sc[-1]] = []
            alts_sc[mods_sc[-1]] = []
        # parse actual mapping
        else:
            key, alt = [x.strip() for x in line.split(':')]
            if key not in keys_vk:
                keys_vk.append(key)
                keys_sc.append(keyboard.key_to_scan_codes(key)[sc_index])
                # add zeroes if "key" is different under several mods, 
                # because "alt" is chosen by index
                if (len(keys_vk) > 0 
                        and len(mods_vk) > 1 
                        and len(keys_vk) -1 > len(alts_vk[mods_sc[-1]])):
                    zero_list = [0 for x in range(keys_vk.index(key))]
                    alts_vk[mods_sc[-1]].extend(zero_list)
                    alts_sc[mods_sc[-1]].extend(zero_list)
            alts_vk[mods_sc[-1]].append(alt)
            # for numpad second element from tuple is needed
            if alt.startswith(numpad_prefix):
                alt = alt.strip(numpad_prefix)
                sc_index = 1
            alts_sc[mods_sc[-1]].append(keyboard.key_to_scan_codes(alt)[sc_index])


def get_config(path_to_config):
    if exists(path_to_config):
        with open(path_to_config) as config:
            parse_config(config)
        config = True
    else:
        config = False
    return(config)


def get_window(kbd_test=False):
    global win
    app = Application()
    if kbd_test:
        app.connect(title=main_app_title)
        win = app.window(title=main_win_title).window(class_name=main_win_class)
    else:
        app.connect(title_re=game_app_title)
        win = app.window(title_re=game_win_title)


def toggle_kbd(event, action):
    mod = cur_toggle
    key = event.scan_code
    key_index = keys_sc.index(key)
    alt = alts_vk[mod][key_index]
    alt_code = alts_sc[mod][key_index]
    msg = f'{{{alt} {action}}}'
    #print(msg)
    win.type_keys(msg, vk_packet=False)


def do_up_down(list_to_iter, keys_to_up, keys_to_down):
    for key in list_to_iter:
        if keyboard.is_pressed(key):
            key_index = list_to_iter.index(key)
            key_up = keys_to_up[key_index]
            key_down = keys_to_down[key_index]
            msg = f'{{{key_up} up}}{{{key_down} down}}'
            win.type_keys(msg, vk_packet=False)
            #print(msg)


def toggle_kbd_all(event):
    global cur_toggle, hooks
    toggle = event.scan_code
    print('toggle started')
    # turn off alts
    if toggle == cur_toggle:
        do_up_down(keys_sc, alts_vk[toggle], keys_vk)
        cur_toggle = None
        keyboard.unhook_all()
        bind_mods()
        if toggle in shift_sc:
            do_up_down(alts_sc[toggle], alts_vk[toggle], keys_vk)
        do_up_down(
            [key.upper() for key in keys_vk],
            alts_vk[toggle], keys_vk
        )
        print('unhooked')
    # turn on alts
    elif cur_toggle == None:
        cur_toggle = toggle
        do_up_down(keys_sc, keys_vk, alts_vk[toggle])
        for key in keys_sc:
            hooks.append(keyboard.on_press_key(
                key, lambda event: toggle_kbd(event, 'down'), suppress=True
                ))
            hooks.append(keyboard.on_release_key(
                key, lambda event: toggle_kbd(event, 'up'), suppress=True
                ))
        print('hooked')
    # alts are on, change mapping for alts
    else:
        do_up_down(alts_sc[cur_toggle], alts_vk[cur_toggle], alts_vk[toggle])
        do_up_down(
            [key.upper() for key in keys_vk],
            alts_vk[cur_toggle], alts_vk[toggle]
        )
        cur_toggle = toggle
        print('change toggle')


def bind_mods():
    for sc in mods_sc:
        keyboard.on_press_key(sc, toggle_kbd_all)


if __name__ == "__main__":
    if get_config(path_to_config):
        get_window()
        bind_mods()
        keyboard.wait()
    else:
        print(f'config "{path_to_config}" not found')