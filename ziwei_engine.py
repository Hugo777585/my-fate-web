import datetime

def calculate_ziwei(birth_year, birth_month, birth_day, birth_hour_index):
    dz_list = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    palace_names = ['命宮', '兄弟', '夫妻', '子女', '財帛', '疾厄', '遷移', '交友', '官祿', '田宅', '福德', '父母']
    month_start = 2 
    ming_palace_idx = (month_start + (birth_month - 1) - birth_hour_index) % 12
    
    full_palaces = {}
    for i in range(12):
        current_dz_idx = (ming_palace_idx + i) % 12
        palace_name = palace_names[i]
        full_palaces[dz_list[current_dz_idx]] = {
            'name': palace_name,
            'stars': []
        }
        
    ziwei_pos_idx = (birth_day % 12) 
    ziwei_dz = dz_list[ziwei_pos_idx]
    if ziwei_dz in full_palaces:
        full_palaces[ziwei_dz]['stars'].append('紫微')
        
    tianfu_pos_idx = (4 - ziwei_pos_idx) % 12
    tianfu_dz = dz_list[tianfu_pos_idx]
    if tianfu_dz in full_palaces:
        full_palaces[tianfu_dz]['stars'].append('天府')

    return {
        'palaces': full_palaces,
        'ming_palace': dz_list[ming_palace_idx],
        'basic_info': {
            'year': birth_year,
            'month': birth_month,
            'day': birth_day,
            'hour': dz_list[birth_hour_index]
        }
    }
