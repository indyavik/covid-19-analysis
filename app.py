from chalice import Chalice, Response
import chalicelib.processor as processor


app = Chalice(app_name='covid-19-analysis')


@app.route('/')
def index():

    res = processor.analyze()

    if res.get("error") is None: 
        return {"response": res }
    else:
        return Response(body={'response': res.get("error") },
                    headers={'Content-Type': 'text/json'},
                    status_code=400)
