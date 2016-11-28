from txhttputil import addTupleType, Tuple, TupleField


@addTupleType
class PeekSwVersionTuple(Tuple):
    __tupleType__ = "peek_platform.PeekSwVersionTuple"

    name = TupleField(comment="The name of this component, papp_name or peek_platform")
    version = TupleField(comment="The version of this component")
