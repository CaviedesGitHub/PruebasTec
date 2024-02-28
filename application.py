from operator import and_
from flask_restful import Api
from flask_jwt_extended import JWTManager
import random
import os
from flask_cors import CORS

from flask import Flask, request
def create_app(config_name, settings_module='config.ProductionConfig'):
    app=Flask(__name__)
    app.config.from_object(settings_module)
    return app


settings_module = os.getenv('APP_SETTINGS_MODULE','config.ProductionConfig')
application = create_app('default', settings_module)
app_context=application.app_context()
app_context.push()


import enum
from flask_sqlalchemy import SQLAlchemy
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields
from sqlalchemy import DateTime, Date
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Resultado(enum.Enum):
    APROBADO = 1
    DESAPROBADO = 2

class Pruebas(db.Model):
    __tablename__ = 'pruebas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cand = db.Column(db.Integer, nullable=False, default=0)
    id_habil = db.Column(db.Integer, nullable=False)
    nota = db.Column(db.Integer, nullable=False, default=0)  
    resultado = db.Column(db.Enum(Resultado), nullable=False, default=Resultado.DESAPROBADO)  
    
    def __init__(self, *args, **kw):
        super(Pruebas, self).__init__(*args, **kw)

    def get_id(self):
        return self.id

    def save(self):
        if not self.id:
            db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_by_id(id):
        return Pruebas.query.get(id)

    @staticmethod
    def get_by_cand(id_cand):
        return Pruebas.query.filter_by(id_cand=id_cand).all()

    @staticmethod
    def get_count():
        return Pruebas.query.count()

    @staticmethod
    def get_count_cand(id_cand):
        return Pruebas.query.filter_by(id_cand=id_cand).count()
    
    @staticmethod
    def get_test_by_cand_habil(idCand, idHabil):
        return Pruebas.query.filter(and_(Pruebas.id_cand==idCand, Pruebas.id_habil==idHabil)).first()

class EnumADiccionario(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        else:
            return value.name #{'llave':value.name, 'valor':value.value} #{value.name}  #{'llave':value.name, 'valor':value.value}
    
class PruebasSchema(SQLAlchemyAutoSchema):
    resultado=EnumADiccionario(attribute=('resultado'))
    class Meta:
        model = Pruebas
        include_relationships = True
        load_instance = True

prueba_schema = PruebasSchema()

db.init_app(application)
db.create_all()


CORS(application)


from flask import request
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, get_jwt
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
#from auth.modelos.modelos import db, Usuario, UsuarioSchema, UserType


prueba_schema = PruebasSchema()

class VistaPruebas(Resource):
    def post(self):
        print("Creando Prueba")
        print(request.json)
        try:
            np=Pruebas()
            np.id_cand=request.json.get("id_cand")
            np.id_habil=request.json.get("id_habil")
            np.nota=request.json.get("nota", 0)
            np.resultado=Resultado[request.json.get("resultado")]
            prueba=Pruebas.get_test_by_cand_habil(np.id_cand, np.id_habil)
            if prueba is not None:
               return {"mensaje": "Prueba no se pudo crear: Esta prueba ya existe."}, 400
            db.session.add(np)
            db.session.commit()
            return {"Prueba": prueba_schema.dump(np)}, 201
        except Exception as inst:
            db.session.rollback()
            print(type(inst))    # the exception instance
            #print(inst)
            print("Prueba no se pudo crear.")
            return {"Mensaje: ":"Error: Prueba no se pudo crear."+str(type(inst))}, 500

class VistaPruebasCalificacion(Resource):
    def post(self, id_examen):
        print("Actualiza Calificacion de un Examen")
        print("id_examen")
        print(id_examen)
        print(request.json)
        try:
            nota=int(request.json.get("nota"))
            if nota is None:
               return {"mensaje": "Prueba no se pudo actualizar: falta la nota."}, 400
            prueba=Pruebas.query.get_or_404(id_examen)
            if prueba is None:
               return {"mensaje": "Prueba no se pudo actualizar: La prueba indicada NO existe."}, 400
            prueba.nota=nota
            if prueba.nota<60:
                prueba.resultado="DESAPROBADO"
            else:
                prueba.resultado="APROBADO"
            db.session.add(prueba)
            db.session.commit()
            return {"Prueba": prueba_schema.dump(prueba)}, 201
        except Exception as inst:
            db.session.rollback()
            print(type(inst))    # the exception instance
            #print(inst)
            print("Prueba no se pudo actualizar.")
            return {"Mensaje: ":"Error: Prueba no se pudo actualizar."+str(type(inst))}, 500

class VistaPruebasCandidato(Resource):
    def get(self, id_cand):
        print("Consultar Pruebas por Candidato")
        try:
            lstPruebas= Pruebas.get_by_cand(id_cand)
            return  [prueba_schema.dump(p) for p in lstPruebas], 200
        except Exception as inst:
            print(type(inst))    # the exception instance
            #print(inst)
            print("No se pudo obtener las pruebas de un candidato.")
            return {"Mensaje: ":"Error: No se pudo obtener la informacion de las pruebas del candidato."}, 500

class VistaPruebasParam(Resource):
    def post(self):
        print("Consultar Pruebas Parametrizadas")
        print("json: ")
        print(request.json)
        try:
            max=request.json.get("max", 50)
            num_pag=request.json.get("num_pag", 1)
            order=request.json.get("order", "ASC")
            candidato=request.json.get("candidato", "")
            habilidad=request.json.get("habilidad", "")
            nota=request.json.get("nota", 0)
            resultado=request.json.get("resultado", "")
            
            lstNumCand=request.json.get("lstNumCand", [0])
            print("lstNumCand")
            print(lstNumCand)

            lstNumHabil=request.json.get("lstNumHabil", [0])
            print("lstNumHabil")
            print(lstNumHabil)

            if lstNumCand==[-1] and lstNumHabil==[-1]:
                numExamenes=Pruebas.get_count()
                lstExamenes=db.session.query(Pruebas.id, 
                                            Pruebas.id_cand,
                                            Pruebas.id_habil,
                                            Pruebas.nota,
                                            Pruebas.resultado,
                            ).order_by(Pruebas.nota.desc()
                            ).paginate(page=num_pag, per_page=max, error_out=False)
            elif lstNumCand!=[-1] and lstNumHabil!=[-1]:
                numExamenes=db.session.query(Pruebas.id, 
                                            Pruebas.id_cand,
                                            Pruebas.id_habil,
                                            Pruebas.nota,
                                            Pruebas.resultado,
                            ).filter(Pruebas.id_cand.in_(lstNumCand)
                            ).filter(Pruebas.id_habil.in_(lstNumHabil)
                            ).count()
                lstExamenes=db.session.query(Pruebas.id, 
                                            Pruebas.id_cand,
                                            Pruebas.id_habil,
                                            Pruebas.nota,
                                            Pruebas.resultado,
                            ).filter(Pruebas.id_cand.in_(lstNumCand)
                            ).filter(Pruebas.id_habil.in_(lstNumHabil)
                            ).order_by(Pruebas.nota.desc()
                            ).paginate(page=num_pag, per_page=max, error_out=False)
            elif lstNumCand==[-1]:
                numExamenes=db.session.query(Pruebas.id, 
                                            Pruebas.id_cand,
                                            Pruebas.id_habil,
                                            Pruebas.nota,
                                            Pruebas.resultado,
                            ).filter(Pruebas.id_habil.in_(lstNumHabil)
                            ).count()
                lstExamenes=db.session.query(Pruebas.id, 
                                            Pruebas.id_cand,
                                            Pruebas.id_habil,
                                            Pruebas.nota,
                                            Pruebas.resultado,
                            ).filter(Pruebas.id_habil.in_(lstNumHabil)
                            ).order_by(Pruebas.nota.desc()
                            ).paginate(page=num_pag, per_page=max, error_out=False)
            elif lstNumHabil==[-1]:
                numExamenes=db.session.query(Pruebas.id, 
                                            Pruebas.id_cand,
                                            Pruebas.id_habil,
                                            Pruebas.nota,
                                            Pruebas.resultado,
                            ).filter(Pruebas.id_cand.in_(lstNumCand)
                            ).count()
                lstExamenes=db.session.query(Pruebas.id, 
                                            Pruebas.id_cand,
                                            Pruebas.id_habil,
                                            Pruebas.nota,
                                            Pruebas.resultado,
                            ).filter(Pruebas.id_cand.in_(lstNumCand)
                            ).order_by(Pruebas.nota.desc()
                            ).paginate(page=num_pag, per_page=max, error_out=False)
            return {'Examenes': [prueba_schema.dump(e) for e in lstExamenes], 'totalCount': numExamenes}, 200
        except Exception as inst:
            print(type(inst))    # the exception instance
            #print(inst)
            print("No se pudo obtener las pruebas.")
            return {"Mensaje: ":"Error: No se pudo obtener la informacion de las pruebas."}, 500


class VistaPing(Resource):
    def get(self):
        print("pong")
        return {"Mensaje":"Pong"}, 200


api = Api(application)
api.add_resource(VistaPruebas, '/pruebas')
api.add_resource(VistaPruebasCandidato, '/pruebasCandidato/<int:id_cand>')
api.add_resource(VistaPruebasParam, '/pruebasParam')
api.add_resource(VistaPruebasCalificacion, '/pruebasCalificacion/<int:id_examen>')
api.add_resource(VistaPing, '/pruebas/ping')


jwt = JWTManager(application)


if Pruebas.get_count()==0:
    print("Creando Pruebas.")
    regT=0
    with open("./pruebas.txt") as archivo:
        for linea in archivo:
            try:
                campos=linea.split(sep='|')
                cn=Pruebas()
                cn.id_cand=int(campos[0])
                cn.id_habil=int(campos[1])
                cn.nota=int(campos[2])
                cn.resultado=Resultado.APROBADO  #Resultado campos[3]
                db.session.add(cn)
                db.session.commit()
                regT=regT+1
                print("===================")
                print(regT)
            except Exception as inst:
                db.session.rollback()
                print(type(inst))    # the exception instance
                print(inst)
                print("Prueba no se pudo crear.")
