class BeachNotFoundError(Exception):
    def __init__(self, beach_id: str):
        super().__init__(f"praia não encontrada: {beach_id}")
        self.beach_id = beach_id


class NoStoredConditionError(Exception):
    def __init__(self, beach_id: str):
        super().__init__(f"nenhuma condição armazenada ainda para a praia: {beach_id}")
        self.beach_id = beach_id
