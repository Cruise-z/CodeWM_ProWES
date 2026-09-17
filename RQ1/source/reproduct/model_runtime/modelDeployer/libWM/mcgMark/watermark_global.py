# Copyright 2024 MCGMT.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ===============================================================
# watermark_global.py
# Description: This file contains global variables and functions
#              for watermarking process management.
# ===============================================================
_global_dict = {}
_global_dict["water_round"] = 1
_global_dict["is_ready_new_round"] = False

def set_value(key, value):
    _global_dict[key] = value

def get_value(key):
    try:
        return _global_dict[key]
    except:
        return None
    
def get_lastest_tele_count():
    return get_value("latest_tele_count")

def set_lastest_tele_count(tele_count):
    set_value("latest_tele_count", tele_count)

def reset_water_round():
    set_value("water_round", 1)

def get_water_round():
    return get_value("water_round")

def new_water_round():
    water_round = get_water_round() + 1
    set_value("water_round", water_round)
    reset_ready_new_round()


def set_ready_new_round():
    set_value("is_ready_new_round", True)

def reset_ready_new_round():
    set_value("is_ready_new_round", False)

def get_ready_new_round():
    return get_value("is_ready_new_round")

First_watermark_token = {}

second_watermark_token = []
