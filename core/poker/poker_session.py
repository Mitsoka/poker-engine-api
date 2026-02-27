from pokerkit import (
    Automation,
    NoLimitTexasHoldem,
    State,
    Hand
)
from typing import Optional, List, Dict, Any, Tuple
import logging

from core.poker.poker_enums import PokerAction, GamePhase


logger = logging.getLogger(__name__)
    

class PokerGameSession:
    def __init__(
        self,
        player_count: int,
        starting_stacks: Tuple[int, ...],
        small_blind: int = 50,
        big_blind: int = 100,
    ):
        self.player_count = player_count
        self.starting_stacks = starting_stacks
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.min_bet = big_blind
        
        self.game_config = {
            "automations": (
                Automation.ANTE_POSTING,
                Automation.BET_COLLECTION,
                Automation.BLIND_OR_STRADDLE_POSTING,
                Automation.CARD_BURNING,
                Automation.HOLE_DEALING,
                Automation.BOARD_DEALING,
                Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
                Automation.HAND_KILLING,
                Automation.CHIPS_PUSHING,
                Automation.CHIPS_PULLING,
            ),
            "ante_trimming_status": True,
            "raw_antes": 0,
            "raw_blinds_or_straddles": (self.small_blind, self.big_blind),
            "min_bet": self.min_bet,
        }
        
        self.game = NoLimitTexasHoldem(**self.game_config)
        self.state: Optional[State] = None
        self.hand_number = 0
        
        self._start_new_hand()
    
    def _start_new_hand(self) -> None:
        self.hand_number += 1
        self.state = self.game.create_state(
            **self.game_config,
            raw_starting_stacks=self.starting_stacks,
            player_count=self.player_count,
        )
        logger.info(f"Started hand #{self.hand_number}")
    
    def process_move(self, player_id: int, move: str, amount: int = 0) -> Dict[str, Any]:
        if not self.state:
            return {"success": False, "error": "Jogo não iniciado"}
        
        if not self.state.status:
            return {"success": False, "error": "Mão atual já terminou"}
        
        current_player = self.state.actor_index
        if current_player != player_id:
            return {
                "success": False, 
                "error": f"Não é seu turno. Turno do jogador {current_player}"
            }
        
        try:
            if move in ["check", "call"]:
                self.state.check_or_call()
                logger.info(f"Player {player_id} checked/called")
                
            elif move == "fold":
                self.state.fold()
                logger.info(f"Player {player_id} folded")
                
            elif move in ["bet", "raise"]:
                if amount <= 0:
                    return {"success": False, "error": "Valor inválido para aposta"}
                
                min_raise = self.state.min_completion_betting_or_raising_amount
                if amount < min_raise:
                    return {
                        "success": False, 
                        "error": f"Valor mínimo para raise é {min_raise}"
                    }
                
                self.state.complete_bet_or_raise_to(amount)
                logger.info(f"Player {player_id} raised to {amount}")
                
            else:
                return {"success": False, "error": f"Ação inválida: {move}"}
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error processing move: {e}")
            return {"success": False, "error": str(e)}
    
    def get_game_state(self, player_id: Optional[int] = None) -> Dict[str, Any]:
        if not self.state:
            return {"phase": "waiting", "message": "Aguardando início do jogo"}
        
        phase = self._get_current_phase()
        
        pots = self._calculate_pots()
        
        state = {
            "hand_number": self.hand_number,
            "phase": phase.value,
            "pot": pots["total"],
            "pots": pots,
            "board_cards": [str(card) for card in self.state.board_cards],
            "players": self._get_players_info(),
            "current_player": self.state.actor_index,
            "min_raise": self.state.min_completion_betting_or_raising_to_amount,
            "active": self.state.status,
            "last_action": self._get_last_action()
        }
        
        if player_id is not None and 0 <= player_id < self.player_count:
            hole_cards = self.state.hole_cards[player_id]
            if hole_cards:
                state["hole_cards"] = [str(card) for card in hole_cards]
        
        return state
    
    def _get_current_phase(self) -> GamePhase:
        if not self.state:
            return GamePhase.PRE_FLOP
        
        board_cards = len(self.state.board_cards)
        
        if board_cards == 0:
            return GamePhase.PRE_FLOP
        elif board_cards == 3:
            return GamePhase.FLOP
        elif board_cards == 4:
            return GamePhase.TURN
        elif board_cards == 5:
            if self.state.status:
                return GamePhase.RIVER
            else:
                return GamePhase.SHOWDOWN
        
        return GamePhase.PRE_FLOP
    
    def _calculate_pots(self) -> Dict[str, int]:
        if not self.state:
            return {"total": 0, "main": 0, "side": 0}
        
        pot_amounts = list(self.state.pot_amounts)
        total_pot = sum(pot_amounts)
        main_pot = pot_amounts[0] if pot_amounts else 0
        side_pot = pot_amounts[1] if len(pot_amounts) > 1 else 0
        
        return {
            "total": total_pot,
            "main": main_pot,
            "side": side_pot
        }
    
    def _get_players_info(self) -> List[Dict[str, Any]]:
        players = []
        
        for i in range(self.player_count):
            if not self.state:
                players.append({
                    "id": i,
                    "stack": self.starting_stacks[i],
                    "active": True,
                    "bet": 0
                })
                continue
                
            players.append({
                "id": i,
                "stack": self.state.stacks[i],
                "active": self.state.statuses[i],
                "bet": self.state.bets[i],
                "folded": self.state.folded_status
            })
        
        return players
        
    
    def _get_last_action(self) -> Optional[Dict[str, Any]]:
        if not self.state or not self.state.operations:
            return None
        
        last_op = self.state.operations[-1]
        
        return {
            "type": last_op.__class__.__name__,
            "player": getattr(last_op, "player_index", None),
            "amount": getattr(last_op, "amount", None)
        }
        
    
    def get_current_player(self) -> Optional[int]:
        return self.state.actor_index if self.state and self.state.status else None
        
    
    def is_hand_complete(self) -> bool:
        return self.state is not None and not self.state.status
        
    
    def get_hand_result(self) -> Dict[str, Any]:
        if not self.state or self.state.status:
            return {"message": "Mão ainda não terminou"}
        
        active_players = [
            i for i in range(self.player_count)
            if self.state.hole_cards[i] and not self.state.folded_statuses[i]
        ]
        
        if not active_players:
            return {"message": "Nenhum jogador ativo"}
        
        hands = {}
        hand_values = {}
        
        for i in active_players:
            hand = self.state.get_hand(i, 0, 0)
            hands[i] = str(hand)
            hand_values[i] = hand
        
        if hand_values:
            best_hand = max(hand_values.values())
            winners = [i for i, h in hand_values.items() if h == best_hand]
        else:
            winners = []
        
        pot_distribution = self._calculate_pot_distribution(winners)
        
        
        self.starting_stacks = tuple(self.state.stacks)
        
        return {
            "winners": winners,
            "hands": {str(i): str(hands[i]) for i in hands},
            "pot_distribution": pot_distribution,
            "message": f"Vencedor(es): {', '.join(map(str, winners))}"
        }
        
    
    def _calculate_pot_distribution(self, winners: List[int]) -> Dict[str, int]:
        if not self.state or not winners:
            return {}
        
        total_pot = sum(self.state.pot_amounts)
        share = total_pot // len(winners)
        remainder = total_pot % len(winners)
        
        distribution = {}
        for i, winner in enumerate(winners):
            distribution[str(winner)] = share + (1 if i < remainder else 0)
        
        return distribution
        
    
    def next_hand(self) -> bool:
        if self.state and self.state.status:
            return False
        
        self._start_new_hand()
        return True



#class PokerRoom:
#    def __init__(self, room_id: str):
#        self.room_id = room_id
#        self.players: List[Dict[str, Any]] = []
#        self.stacks: List[int] = []
#        self.game_session: Optional[PokerGameSession] = None
#        self.created_at = None  # Adicionar timestamp
#        
#    def add_player(self, player_id: str, chips: int, username: str = "") -> int:
#        """Adiciona jogador à sala. Retorna o índice do jogador."""
#        player_index = len(self.players)
#        self.players.append({
#            "id": player_id,
#            "index": player_index,
#            "chips": chips,
#            "username": username,
#            "connected": True
#        })
#        self.stacks.append(chips)
#        return player_index
#    
#    def remove_player(self, player_id: str) -> bool:
#        """Remove jogador da sala"""
#        for i, player in enumerate(self.players):
#            if player["id"] == player_id:
#                player["connected"] = False
#                # Manter na lista mas marcar como desconectado
#                return True
#        return False
#    
#    def can_start_game(self) -> Tuple[bool, str]:
#        """Verifica se o jogo pode começar"""
#        active_players = [p for p in self.players if p["connected"]]
#        
#        if len(active_players) < 2:
#            return False, "Mínimo de 2 jogadores necessário"
#        
#        if self.game_session:
#            return False, "Jogo já está em andamento"
#        
#        return True, "OK"
#    
#    def start_game(self) -> Tuple[bool, str]:
#        """Inicia o jogo"""
#        can_start, message = self.can_start_game()
#        if not can_start:
#            return False, message
#        
#        active_players = [p for p in self.players if p["connected"]]
#        active_stacks = [self.stacks[p["index"]] for p in active_players]
#        
#        self.game_session = PokerGameSession(
#            player_count=len(active_players),
#            starting_stacks=tuple(active_stacks),
#            small_blind=50,
#            big_blind=100
#        )
#        
#        return True, "Jogo iniciado"