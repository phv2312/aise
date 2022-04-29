import os
import time
import numpy as np
import cv2
import tempfile
from datetime import datetime
from celery import Celery
from webapp.database import SessionLocal
from webapp import schemas, crud


db = SessionLocal()
celery_app = Celery('worker', broker=os.getenv('BROKER_URL'), backend=os.getenv('BACKEND_URL'))
celery_app.conf.task_serializer = 'pickle'
celery_app.conf.result_serializer = 'pickle'
celery_app.conf.accept_content = ['application/json', 'application/x-python-serialize']


def load_image_into_numpy_array(data):
    np_image = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
    cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return frame


def get_temp_path(np_image):
    temp_dir = tempfile.mkdtemp(dir=os.getenv('STORAGE_DIR', 'images'))
    output_path = os.path.join(temp_dir, 'image.png')

    cv2.imwrite(output_path, np_image)

    return output_path


def interpolate(reference_image: np.ndarray, target_image: np.ndarray):
    reference_image_resized = cv2.resize(reference_image, (512, 512))
    target_image_resized = cv2.resize(target_image, (512, 512))

    result_image = np.concatenate([reference_image_resized, target_image_resized], axis=1)
    return result_image


@celery_app.task
def start_interpolation_job(reference_buffer_data, target_buffer_data, job_id):
    time.sleep(10)



    #
    try:
        reference_np_image = load_image_into_numpy_array(reference_buffer_data)
        reference_output_path = get_temp_path(reference_np_image)
        reference_image = schemas.Image(created_at=str(datetime.now()), url=reference_output_path, is_reference=True,
                                        job_id=job_id)
        crud.create_image(db, reference_image)

        target_np_image = load_image_into_numpy_array(target_buffer_data)
        target_output_path = get_temp_path(target_np_image)
        target_image = schemas.Image(created_at=str(datetime.now()), url=target_output_path, is_reference=False,
                                     job_id=job_id)
        crud.create_image(db, target_image)

        # Result
        interpolating_np_image = interpolate(reference_np_image, target_np_image)
        result_output_path = get_temp_path(interpolating_np_image)
        result = schemas.Result(created_at=str(datetime.now()), url=result_output_path, job_id=job_id)
        crud.create_interpolating_result(db, result)

        crud.update_job(db, job_id, 'SUCCESS')

    except Exception as e:
        print (e)
        crud.update_job(db, job_id, 'FAILURE')

    return
