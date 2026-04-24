# -*- coding: utf-8 -*-

import json
import time

EPSILON = 1e-9
PERF_REPEAT = 10

# -------------------------
# 유틸리티 함수
# -------------------------
def normalize_label(label):
    if label is None:
        return None
    s = str(label).strip()
    mapping = {"+": "Cross", "x": "X", "X": "X", "cross": "Cross", "Cross": "Cross"}
    return mapping.get(s, s)

def safe_get(dct, key, default=None):
    return dct.get(key, default) if isinstance(dct, dict) else default

# -------------------------
# 행렬 입력/검증
# -------------------------
def read_matrix_once(n, prompt_name="matrix"):
    """한 번의 입력 시도: 실패하면 None 반환"""
    
    rows = []
    for i in range(n):
        raw = input(f"{prompt_name} {i+1}행: ").strip()
        parts = raw.split()
        if len(parts) != n:
            print(f"입력 형식 오류: 각 줄에 {n}개의 숫자를 공백으로 구분해 입력하세요.")
            return None
        try:
            row = [float(x) for x in parts]
        except ValueError:
            print("입력 형식 오류: 숫자 파싱 실패. 숫자만 입력하세요.")
            return None
        rows.append(row)
    return rows

def read_matrix(n, name="matrix"):
    """올바른 입력이 들어올 때까지 반복 요청"""
    while True:
        m = read_matrix_once(n, name)
        if m is not None:
            return m
        print("다시 입력하세요.")

# -------------------------
# MAC 연산 (외부 라이브러리 금지)
# -------------------------
def mac_score(filter_matrix, pattern_matrix):
    """n x n 행렬에 대해 element-wise multiply and accumulate"""
    if filter_matrix is None or pattern_matrix is None:
        raise ValueError("filter_matrix 또는 pattern_matrix가 None입니다.")
    n = len(filter_matrix)
    # 크기 검증 (정사각)
    if n == 0 or any(len(row) != n for row in filter_matrix):
        raise ValueError("filter_matrix가 정사각형이 아닙니다.")
    if len(pattern_matrix) != n or any(len(row) != n for row in pattern_matrix):
        raise ValueError("pattern_matrix 크기가 filter와 일치하지 않습니다.")
    total = 0.0
    for i in range(n):
        fi = filter_matrix[i]
        pi = pattern_matrix[i]
        for j in range(n):
            total += fi[j] * pi[j]
    return total

def compare_scores(score_cross, score_x):
    if abs(score_cross - score_x) < EPSILON:
        return "UNDECIDED"
    return "Cross" if score_cross > score_x else "X"

# -------------------------
# 성능 측정
# -------------------------
def measure_mac_time(n, repeat=PERF_REPEAT):
    # 더 현실적인 측정: 동일한 임시 행렬을 만들어 연산만 반복
    a = [[1.0 for _ in range(n)] for _ in range(n)]
    b = [[1.0 for _ in range(n)] for _ in range(n)]
    times = []
    # 워밍업 1회
    mac_score(a, b)
    for _ in range(repeat):
        t0 = time.perf_counter()
        mac_score(a, b)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)  # ms
    avg_ms = sum(times) / len(times)
    return avg_ms, n * n

def performance_analysis(sizes):
    print("\n=== 성능 분석 (각 크기 평균, {}회 반복) ===".format(PERF_REPEAT))
    print(f"{'크기':>8} | {'평균 시간(ms)':>14} | {'연산 횟수(N^2)':>14}")
    print("-" * 44)
    for n in sizes:
        avg_ms, ops = measure_mac_time(n)
        print(f"{str(n)+'x'+str(n):>8} | {avg_ms:14.6f} | {ops:14}")

# -------------------------
# 모드 1: 콘솔 입력 (3x3)
# -------------------------
def mode_console():
    print("=== 3x3 콘솔 입력 모드 ===")
    filter_a = read_matrix(3, "필터 A")
    filter_b = read_matrix(3, "필터 B")
    pattern = read_matrix(3, "패턴")

    t0 = time.perf_counter()
    score_a = mac_score(filter_a, pattern)
    score_b = mac_score(filter_b, pattern)
    t1 = time.perf_counter()

    result = compare_scores(score_a, score_b)
    # 표준 라벨로 변환: A/B -> Cross/X 아님, 콘솔 모드에서는 A/B로 표기했던 기존 코드와 달리 Cross/X 표준 라벨 사용
    # 여기서는 filter A가 Cross인지 X인지 알 수 없으므로 A/B로 출력
    print("\n--- 결과 ---")
    print(f"필터 A 점수: {score_a}")
    print(f"필터 B 점수: {score_b}")
    print(f"연산 시간: {(t1 - t0) * 1000.0:.6f} ms")
    print(f"판정 결과: {result}  (A if A>B, B if B>A, UNDECIDED if tie)")
    print("\n성능 분석 (3x3):")
    performance_analysis([3])

# -------------------------
# 모드 2: JSON 로드 및 판정
# -------------------------
def mode_json(filename="data.json"):
    print("=== JSON 분석 모드 ===")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {filename}")
        return
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        return

    filters = safe_get(data, "filters", {})
    patterns = safe_get(data, "patterns", {})

    summary = []
    print()
    for key, val in patterns.items():
        # key 형식: size_N_idx 또는 size_N
        try:
            parts = key.split("_")
            if len(parts) < 2:
                raise ValueError("패턴 키 형식 오류")
            size = int(parts[1])
        except Exception:
            print(f"{key}: FAIL (키에서 크기 추출 실패)")
            summary.append((key, "FAIL", "키에서 크기 추출 실패"))
            continue

        pattern = safe_get(val, "input")
        expected_raw = safe_get(val, "expected")
        if pattern is None:
            print(f"{key}: FAIL (pattern 'input' 누락)")
            summary.append((key, "FAIL", "pattern 'input' 누락"))
            continue
        expected = normalize_label(expected_raw)
        if expected is None:
            print(f"{key}: FAIL (expected 누락 또는 인식 불가)")
            summary.append((key, "FAIL", "expected 누락 또는 인식 불가"))
            continue

        filter_key = f"size_{size}"
        if filter_key not in filters:
            print(f"{key}: FAIL (필터 {filter_key} 없음)")
            summary.append((key, "FAIL", f"필터 {filter_key} 없음"))
            continue

        filter_entry = filters[filter_key]
        if not isinstance(filter_entry, dict):
            print(f"{key}: FAIL (필터 형식 오류: Cross/X 딕셔너리 기대)")
            summary.append((key, "FAIL", "필터 형식 오류"))
            continue

        filter_cross = filter_entry.get("Cross")
        filter_x = filter_entry.get("X")
        if filter_cross is None or filter_x is None:
            print(f"{key}: FAIL (Cross/X 필터 없음)")
            summary.append((key, "FAIL", "Cross/X 필터 없음"))
            continue

        # 크기 검증
        if len(filter_cross) != size or len(filter_x) != size or len(pattern) != size:
            print(f"{key}: FAIL (크기 불일치)")
            summary.append((key, "FAIL", "크기 불일치"))
            continue

        # MAC 연산 (시간 측정: 연산 구간만)
        t0 = time.perf_counter()
        try:
            score_cross = mac_score(filter_cross, pattern)
            score_x = mac_score(filter_x, pattern)
        except Exception as e:
            print(f"{key}: FAIL (연산 중 오류: {e})")
            summary.append((key, "FAIL", f"연산 오류: {e}"))
            continue
        t1 = time.perf_counter()

        result = compare_scores(score_cross, score_x)

        if result == "UNDECIDED":
            status = "FAIL"
            reason = "동점 발생"
        elif result == expected:
            status = "PASS"
            reason = None
        else:
            status = "FAIL"
            reason = None

        print(f"{key}: Cross={score_cross}, X={score_x}, 판정={result}, expected={expected}, {status}")
        summary.append((key, status, reason))

    # 전체 성능 분석 (3,5,13,25)
    performance_analysis([3,5,13,25])

    total_count = len(summary)
    pass_count = sum(1 for _, status, _ in summary if status == "PASS")
    fail_count = sum(1 for _, status, _ in summary if status == "FAIL")

    print("\n=== 전체 집계 ===")
    print(f"전체 테스트 수: {total_count}")
    print(f"통과 수: {pass_count}")
    print(f"실패 수: {fail_count}")

    # 요약 출력
    print("\n=== 결과 요약 ===")
    for item in summary:
        key, status, reason = item
        if reason:
            print(f"{key}: {status} ({reason})")
        else:
            print(f"{key}: {status}")

# -------------------------
# main 함수: 메뉴 반복 루프
def main():
    while True:
        try:
            print("모드 선택:")
            print(" 1 = 콘솔 입력")
            print(" 2 = JSON 입력")
            print(" q = 종료")
            mode = input("선택: ").strip()
        except KeyboardInterrupt:
            print("\n사용자 중단")
            break

        if mode == "1":
            mode_console()
        elif mode == "2":
            mode_json()
        elif mode.lower() in ("q", "quit", "exit"):
            print("프로그램 종료")
            break
        else:
            print("잘못된 모드 선택. 1, 2 또는 q를 입력하세요.")

if __name__ == "__main__":
    main()
