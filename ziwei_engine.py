import datetime
from iztro import Astro

def calculate_ziwei(birth_year, birth_month, birth_day, birth_hour_index):
    # Convert 24-hour format to 12-branch index if needed
    if birth_hour_index not in range(12):
        birth_hour_index = (birth_hour_index // 2) % 12

    dz_list = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    palace_names = ['命宮', '兄弟', '夫妻', '子女', '財帛', '疾厄', '遷移', '交友', '官祿', '田宅', '福德', '父母']

    # Use iztro-py for accurate Ziwei Dou Shu calculation
    astro = Astro.new(birth_year, birth_month, birth_day, birth_hour_index * 2, 0, 'male')  # Assuming male, can be adjusted
    chart = astro.get_chart()

    full_palaces = {}
    for i in range(12):
        palace_name = palace_names[i]
        dz = dz_list[i]
        stars = []

        # Get stars for this palace
        palace_data = chart.get_palace(dz)
        if palace_data:
            # Add main stars
            main_stars = palace_data.get('main_stars', [])
            for star in main_stars:
                stars.append(star.name)

            # Add minor stars
            minor_stars = palace_data.get('minor_stars', [])
            for star in minor_stars:
                stars.append(star.name)

        full_palaces[dz] = {
            'name': palace_name,
            'stars': stars
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
