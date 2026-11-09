"""Chạy lại toàn bộ pipeline tạo dữ liệu: python data_pipeline/run_all.py"""
from data_pipeline import s01_clean_jobs
from data_pipeline import s02_generate_cvs
from data_pipeline import s03_split_export
from data_pipeline import s04_render_files
from data_pipeline import s05_annotation_set

for step in (s01_clean_jobs, s02_generate_cvs, s03_split_export, s04_render_files, s05_annotation_set):
    print(f"\n===== {step.__name__} =====")
    step.main()
