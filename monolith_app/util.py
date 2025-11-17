"""공유 유틸리티 헬퍼 함수"""
import os
from io import BytesIO
from PIL import Image

# EXIF 태그 중 Orientation(방향)을 나타내는 값
EXIF_ORIENTATION = 274

def random_hex_bytes(n_bytes):
    """지정된 바이트 수만큼의 랜덤 문자열을 16진수로 인코딩하여 생성합니다."""
    return os.urandom(n_bytes).hex()

def resize_image(file_p, size):
    """
    이미지 파일을 주어진 크기에 맞게 리사이징하고, 중앙에 위치시킨 후 PNG 형식의 바이트 스트림으로 반환합니다.
    - file_p: 이미지 파일 포인터 (file-like object)
    - size: (너비, 높이) 튜플
    """
    dest_ratio = size[0] / float(size[1])
    try:
        image = Image.open(file_p)
    except IOError:
        print("오류: 이미지를 열 수 없습니다.")
        return None

    # EXIF 데이터를 확인하여 이미지 방향을 보정합니다.
    try:
        exif = dict(image._getexif().items())
        if exif[EXIF_ORIENTATION] == 3: # 180도 회전
            image = image.rotate(180, expand=True)
        elif exif[EXIF_ORIENTATION] == 6: # 270도 회전 (시계 방향)
            image = image.rotate(270, expand=True)
        elif exif[EXIF_ORIENTATION] == 8: # 90도 회전 (시계 방향)
            image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        # EXIF 정보가 없는 경우
        print("EXIF 데이터가 없습니다.")

    source_ratio = image.size[0] / float(image.size[1])

    # 원본 이미지가 목표 크기보다 작으면 스케일링하지 않음
    if image.size[0] < size[0] and image.size[1] < size[1]:
        new_width, new_height = image.size
    # 목표 비율에 맞춰 너비 또는 높이를 기준으로 리사이징
    elif dest_ratio > source_ratio:
        new_height = size[1]
        new_width = int(image.size[0] * size[1] / float(image.size[1]))
    else:
        new_width = size[0]
        new_height = int(image.size[1] * size[0] / float(image.size[0]))
    
    # LANCZOS 필터를 사용하여 고품질로 이미지 리사이징
    image = image.resize((new_width, new_height), resample=Image.LANCZOS)

    # 지정된 크기의 새 RGBA 이미지(배경 투명)를 생성
    final_image = Image.new("RGBA", size)
    # 리사이징된 이미지를 중앙에 배치하기 위한 좌상단 좌표 계산
    topleft = (int((size[0] - new_width) / 2.0),
               int((size[1] - new_height) / 2.0))
    # 최종 이미지에 리사이징된 이미지를 붙여넣기
    final_image.paste(image, topleft)
    
    # 최종 이미지를 메모리 내 바이트 스트림으로 저장
    bytes_stream = BytesIO()
    final_image.save(bytes_stream, 'PNG')
    # 바이트 스트림의 값을 반환
    return bytes_stream.getvalue()
