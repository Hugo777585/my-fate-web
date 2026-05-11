import datetime
from iztro_py import astro

def calculate_ziwei(birth_year, birth_month, birth_day, birth_hour_index):
    # Convert 24-hour format to 12-branch index if needed
    if birth_hour_index not in range(12):
        birth_hour_index = (birth_hour_index // 2) % 12

    dz_list = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    palace_names = ['命宮', '兄弟', '夫妻', '子女', '財帛', '疾厄', '遷移', '交友', '官祿', '田宅', '福德', '父母']

    # Use iztro-py for accurate Ziwei Dou Shu calculation
    chart = astro.by_solar(f'{birth_year}-{birth_month}-{birth_day}', birth_hour_index, '男')

    # Mapping from English to Chinese earthly branches
    branch_map = {
        'ziEarthly': '子', 'chouEarthly': '丑', 'yinEarthly': '寅', 'maoEarthly': '卯',
        'chenEarthly': '辰', 'siEarthly': '巳', 'wuEarthly': '午', 'weiEarthly': '未',
        'shenEarthly': '申', 'youEarthly': '酉', 'xuEarthly': '戌', 'haiEarthly': '亥'
    }

    full_palaces = {}
    for palace in chart.palaces:
        dz = branch_map.get(palace.earthly_branch, palace.earthly_branch)
        stars = []
        main_stars = []
        minor_stars = []
        
        # Add main stars
        for star in palace.major_stars:
            star_name = star.name
            stars.append(star_name)
            main_stars.append(star_name)
        
        # Add minor stars  
        for star in palace.minor_stars:
            star_name = star.name
            stars.append(star_name)
            minor_stars.append(star_name)
            
        full_palaces[dz] = {
            'name': palace.name,  # Keep English name for now, can translate later
            'stars': stars,
            'main_star': main_stars[0] if main_stars else '',
            'minor_stars': minor_stars
        }

    return {
        'palaces': full_palaces,
        'ming_palace': dz_list[0],  # Life palace is always first in standard layout
        'basic_info': {
            'year': birth_year,
            'month': birth_month,
            'day': birth_day,
            'hour': dz_list[birth_hour_index]
        }
    }
