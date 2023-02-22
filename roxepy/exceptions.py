
class InvalidKeyFile(Exception):
    ''' Raised when the key file format is invalid '''
    pass


class InvalidPermissionFormat(Exception):
    ''' Raised when the permission format is invalid'''
    pass


class ROXEKeyError(Exception):
    ''' Raised when there is an ROXEKey error '''
    pass


class ROXEMsigInvalidProposal(Exception):
    ''' Raised when an invalid proposal is queried'''
    pass


class ROXEBufferInvalidType(Exception):
    ''' Raised when trying to encode/decode an invalid type '''
    pass


class ROXEInvalidSchema(Exception):
    ''' Raised when trying to process a schema '''
    pass


class ROXEUnknownObj(Exception):
    ''' Raised when an object is not found in the ABI '''
    pass


class ROXEAbiProcessingError(Exception):
    ''' Raised when the abi action cannot be processed '''
    pass


class ROXESetSameCode(Exception):
    ''' Raised when the code would not change on a set'''
    pass


class ROXESetSameAbi(Exception):
    ''' Raised when the abi would not change on a set'''
    pass
