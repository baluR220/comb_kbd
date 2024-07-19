from os.path import exists
from time import sleep
from threading import Thread

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
bind_on = False
win = None
main_app_title = 'PCSX2  1.6.0'
main_win_title = 'WM Keyboard'
main_win_class = 'SysListView32'
game_app_title = 'Slot:*'
game_win_title = 'Slot:*'


def show_msg(*args, **kwargs):
    print(*args, **kwargs)


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


def get_window_thread():
    # poll existence of main and game application and window.
    # globally change "win" variable for "toggle_kbd" to send keys to.
    global win
    app_main = None
    app_game = None
    win_main = None
    win_game = None
    while True:
        if not app_main:
            try:
                app = Application()
                app.connect(title=main_app_title)
            except Exception:
                pass
            else:
                app_main = app
        else:
            if app_main.is_process_running():
                if not win_main:
                    win_main = app_main.window(title=main_win_title).window(
                        class_name=main_win_class
                    )
                if not win_main.exists():
                    win_main = None
            else:
                app_main = None
        if not app_game:
            try:
                app = Application()
                app.connect(title_re=game_app_title)
            except Exception:
                pass
            else:
                app_game = app
        else:
            if app_game.is_process_running():
                if not win_game:
                    win_game = app_game.window(title_re=game_win_title)
                if not win_game.exists():
                    win_game = None
            else:
                app_game = None
        if win_main:
            win = win_main
        elif win_game:
            win = win_game
        else:
            win = None
        sleep(1)


def toggle_kbd(event, action):
    mod = cur_toggle
    key = event.scan_code
    key_index = keys_sc.index(key)
    alt = alts_vk[mod][key_index]
    alt_code = alts_sc[mod][key_index]
    msg = f'{{{alt} {action}}}'
    win.type_keys(msg, vk_packet=False)


def do_up_down(list_to_iter, keys_to_up, keys_to_down):
    for key in list_to_iter:
        if keyboard.is_pressed(key):
            key_index = list_to_iter.index(key)
            key_up = keys_to_up[key_index]
            key_down = keys_to_down[key_index]
            msg = f'{{{key_up} up}}{{{key_down} down}}'
            win.type_keys(msg, vk_packet=False)


def toggle_kbd_all(event):
    global cur_toggle, hooks
    toggle = event.scan_code
    show_msg('toggle started')
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
        show_msg('kbd unhooked')
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
        show_msg('kbd hooked')
    # alts are on, change mapping for alts
    else:
        do_up_down(alts_sc[cur_toggle], alts_vk[cur_toggle], alts_vk[toggle])
        do_up_down(
            [key.upper() for key in keys_vk],
            alts_vk[cur_toggle], alts_vk[toggle]
        )
        cur_toggle = toggle
        show_msg('change toggle')


def bind_mods():
    global bind_on
    for sc in mods_sc:
        keyboard.on_press_key(sc, toggle_kbd_all)
    bind_on = True


def bind_mods_thread():
    # poll existence of "win" to bind mods or to unhook all bindings
    global bind_on, cur_toggle
    while True:
        if win and not bind_on:
            bind_mods()
            show_msg("bind hooked")
        elif not win and bind_on:
            keyboard.unhook_all()
            bind_on = False
            cur_toggle = None
            show_msg("bind unhooked")
        sleep(0.5)


if __name__ == "__main__":
    if get_config(path_to_config):
        Thread(target=get_window_thread, daemon=True).start()
        Thread(target=bind_mods_thread, daemon=True).start()
        keyboard.wait()
    else:
        show_msg(f'config "{path_to_config}" not found')
