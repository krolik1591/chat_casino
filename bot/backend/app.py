from aiohttp import web
from aiohttp.web_request import Request
import aiohttp_cors

routes = web.RouteTableDef()


@routes.get('/backend')
async def hello(request: Request):
    return web.Response(text="Hello, world")


@routes.post('/backend/create_fortune_wheel')
async def create_fortune_wheel(request: Request):
    form_data = await request.post()
    # form_data.ticket_cost  # is number
    # form_data.date_end  # is future date

    # todo validate and put to db
    return web.Response(text='{"ok": "ok"}')


def run(port=8080, loop=None, bot=None):
    app = web.Application()
    app['bot'] = bot
    app.add_routes(routes)

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*")
    })
    for route in list(app.router.routes()):
        cors.add(route)

    web.run_app(app, port=port, loop=loop)


if __name__ == "__main__":
    run()
