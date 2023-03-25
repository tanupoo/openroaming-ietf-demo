#!/usr/bin/env python

import aiofile
from fastapi import FastAPI, Query, Request, Header, Body, Path
from fastapi import status as httpcode
from fastapi.exceptions import RequestValidationError # debug
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder
from pydantic import Required
from typing import Annotated
from meraki.meraki_asyncio_api import meraki_asyncio_api
import json

def api(config):

    logger = config.logger
    ssid_list = config.ssid_list
    if ssid_list is None:
        print("ERROR: ssid_list must be defined in the config.")
        exit(1)
    if config.server_port:
        server_basename = f"{config.server_basename}:{config.server_port}"
    else:
        server_basename = config.server_basename

    meraki = meraki_asyncio_api(config.loop,
                                logger=config.logger,
                                debug=config.enable_debug)
    meraki.set_apikey(config_api_key_spec=config.api_key_spec)

    fastapi_kwargs = {}
    #fastapi_kwargs = dict(docs_url=None, redoc_url=None, openapi_url=None)
    app = FastAPI(**fastapi_kwargs)


    def get_ssid_spec(ssid_name):
        for x in ssid_list:
            if x.ssid_name == ssid_name:
                return x
        else:
            return None


    def set_ssid_status(obj, ssid_name, result) -> None:
        if result:
            status = result.get("enabled")
            if status == True:
                obj[ssid_name] = { "status": "up" }
                logger.info(f"set_ssid_status(), {ssid_name} is up.")
            elif status == False:
                obj[ssid_name] = { "status": "down" }
                logger.info(f"set_ssid_status(), {ssid_name} is down.")
            else:
                obj[ssid_name] = { "status": "unknown" }
                logger.error(f"set_ssid_status: status=unknown")
        else:
            logger.error(f"set_ssid_status(), {result}")


    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        content = jsonable_encoder(exc.errors())
        logger.error(f"Validation Error: {content}")
        return JSONResponse(
            status_code=httpcode.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": content},
        )


    @app.get(
        "/ui",
        response_description="UI entry point.",
        response_class=HTMLResponse,
        status_code=httpcode.HTTP_200_OK,
    )
    async def get_ui(request: Request):
        html_content = None
        async with aiofile.async_open(f"{config.ui_path}/index.html", "r") as fd:
            html_content = await fd.read()
        ssid_list_js = str([x.ssid_name for x in ssid_list])
        return html_content.replace("__BASE_NAME__",
                                    server_basename).replace("__SSID_LIST__", ssid_list_js)


    @app.get("/v1/status")
    async def api_get_all_ssids_status() -> dict: #ResSSIDStatusList:
        logger.info(f"GET /v1/status")
        resp = {}
        x = resp.setdefault("response", {})
        for v in ssid_list:
            result = await meraki.async_get_ssid(v.network_id, v.ssid_number,
                                                 debug=config.enable_debug)
            set_ssid_status(x, v.ssid_name, result)
        if x:
            return resp
        else:
            logger.error(f"api_get_all_ssids_status(), error")
            return JSONResponse(status_code=httpcode.HTTP_404_NOT_FOUND,
                                content={})


    @app.get("/v1/status/{ssid_name}")
    async def api_get_ssid_status(
            #ssid_name: str = Query(Required, description="SSID name")
            ssid_name: str = Annotated[int, Path(title="SSID name")]
            ) -> dict:
        logger.info(f"GET /v1/status/{ssid_name}")
        resp = {}
        x = resp.setdefault("response", {})
        v = get_ssid_spec(ssid_name)
        if v:
            result = await meraki.async_get_ssid(v.network_id, v.ssid_number,
                                                 debug=config.enable_debug)
            set_ssid_status(x, v.ssid_name, result)
            return resp
        else:
            logger.error(f"api_get_ssid_status(), unknown ssid: {ssid_name}")
            return JSONResponse(status_code=httpcode.HTTP_404_NOT_FOUND,
                                content={})


    @app.put("/v1/status/{ssid_name}")
    async def api_put_ssid_status(
            #ssid_name: str = Query(Required, description="SSID name"),
            ssid_name: str = Annotated[int, Path(title="SSID name")],
            enabled: bool = Query(Required, description="if 'true', try to enable the SSID.")
            ) -> dict:
        logger.info(f"PUT /v1/status/{ssid_name}")
        if enabled is True:
            data = { "enabled": True }
        else:   # enabled is False
            data = { "enabled": False }
        #
        resp = {}
        x = resp.setdefault("response", {})
        v = get_ssid_spec(ssid_name)
        if v:
            result = await meraki.async_put_ssid(v.network_id, v.ssid_number, data,
                                                 debug=config.enable_debug)
            set_ssid_status(x, v.ssid_name, result)
            return resp
        else:
            logger.error(f"api_put_ssid_status(): unknown ssid: {ssid_name}")
            return JSONResponse(status_code=httpcode.HTTP_404_NOT_FOUND,
                                content={})


    from fastapi.staticfiles import StaticFiles
    app.mount("/ui", StaticFiles(directory=config.ui_path, html=True), name="ui")


    return app
