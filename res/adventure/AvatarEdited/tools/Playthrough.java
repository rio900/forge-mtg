import com.badlogic.gdx.Gdx;
import forge.Forge;
import forge.adventure.character.ShopActor;
import forge.adventure.scene.*;
import forge.adventure.stage.WorldStage;
import forge.adventure.util.*;
import forge.adventure.world.WorldSave;
import forge.model.FModel;
import forge.toolbox.FOptionPane;
import forge.toolbox.FOverlay;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public class Playthrough {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    static <T> T render(Callable<T> task) throws Exception {
        var future = new FutureTask<T>(task);
        Gdx.app.postRunnable(future);
        return future.get(90, TimeUnit.SECONDS);
    }
    static List<String> stock(TileMapScene tile) {
        for (int i=0;i<200;i++) if (tile.currentMap().getByID(i) instanceof ShopActor shop &&
                shop.getShopData().name.startsWith("AvatarTown") && shop.getShopData().rewards.size==4) {
            var cards=new ArrayList<String>();
            for(var r:shop.getRewardData()) {
                var c=r.getCard();
                check(Set.of("TLA","TLE").contains(c.getEdition()),c.toString());
                cards.add(c.getName()+"|"+c.getEdition());
            }
            check(new HashSet<>(cards).size()==4,"shop duplicates "+cards);
            return cards;
        }
        throw new AssertionError("missing shop");
    }
    static void approach(forge.adventure.pointofintrest.PointOfInterest point) throws Exception {
        render(()->{
            var world=WorldStage.getInstance();
            var sprite=world.getPlayerSprite();
            var pos=point.getPosition();
            sprite.setPosition(pos.x+40,pos.y);
            var map=Current.world();
            int grid=map.getChunkSize()*map.getTileSize();
            for(var actor:world.getActors())if(actor instanceof forge.adventure.stage.WorldBackground background){
                background.initialize();
                background.loadChunk((int)pos.x/grid,(int)pos.y/grid);
            }
            world.handlePointsOfInterestCollision();
            var marker=world.getMapSprite(point);
            if(marker==null)for(var actor:world.getSpriteGroup().getChildren())
                if(actor instanceof forge.adventure.stage.PointOfInterestMapSprite poi &&
                     poi.getPointOfInterest().getID().equals(point.getID())){marker=poi;break;}
            check(marker!=null,"missing world marker "+point.getID()+" at "+pos);
            var rect=marker.getBoundingRect();
            sprite.setPosition(rect.x+rect.width/2,rect.y+rect.height/2);
            check(world.handlePointsOfInterestCollision(),"no collision "+rect);
            check(AdventureQuestController.instance().mostRecentPOI.getID().equals(point.getID()),"wrong POI");
            return null;
        });
    }
    static void test() throws Exception {
        long deadline=System.currentTimeMillis()+150000;
        while(!Forge.afterDBloaded && Forge.getCurrentScene()==null && System.currentTimeMillis()<deadline) Thread.sleep(400);
        if(Forge.getCurrentScene()==null)render(()->{Forge.openAdventure();return null;});
        while(Forge.getCurrentScene()==null && System.currentTimeMillis()<deadline)Thread.sleep(400);
        var cfg=Config.instance();
        check(cfg.getPlane().equals("AvatarEdited"),cfg.getPlane());
        check(Path.of(WorldSave.getSaveDir()).toAbsolutePath().normalize().startsWith(Path.of("").toAbsolutePath()),"profile");
        var w=render(()->Files.isRegularFile(Path.of(WorldSave.getSaveFile(1))) && WorldSave.load(1) ? WorldSave.getCurrentSave() : WorldSave.generateNewWorld("AvatarTest",true,0,0,forge.card.ColorSet.fromNames("Green"),
            cfg.getConfigData().difficulties[1],AdventureModes.Standard,0,FModel.getMagicDb().getEditions().get("TLA"),247L));
        render(()->Forge.switchScene(GameScene.instance()));
        Thread.sleep(1800);
        check(render(()->w.save("AvatarTest",1)),"save");
        var points=w.getWorld().getAllPointOfInterest();
        var town=points.stream().filter(p->p.getData().map.contains("/towns/")).findFirst().orElseThrow();
        var tile=render(TileMapScene::instance);
        List<String> first=null;
        for(int i=0;i<2;i++){
            if(i==0)approach(town);
            else render(()->{WorldStage.getInstance().loadPOI(town);return null;});
            var goods=render(()->{check(Forge.getCurrentScene()==tile,"town entrance");return stock(tile);});
            if(first!=null)check(first.equals(goods),"reroll");
            first=goods;
            System.out.println("PLAY town "+town.getData().name+" "+goods);
            render(()->tile.currentMap().exitDungeon(false,false));
            Thread.sleep(900);
        }
        boolean dragon = Boolean.getBoolean("avatar.test.dragon");
        String bossName = dragon ? "Ancient Silver Dragon" : "Slobad";
        var location = points.stream().filter(p -> dragon
                ? Set.of("FortBlue2", "DjinnPalace", "DjinnPalace1", "MerfolkPool5").contains(p.getData().name)
                : p.getData().name.equals("Slobads Factory")).findFirst().orElseThrow();
        int bossId = switch (location.getData().name) {
            case "FortBlue2" -> 55;
            case "DjinnPalace", "DjinnPalace1" -> 105;
            case "MerfolkPool5" -> 62;
            default -> 74;
        };
        String testDeck = System.getProperty("avatar.test.deck", "");
        if (!testDeck.isEmpty()) {
            render(() -> {
                var player = Current.player();
                String path = switch (testDeck) {
                    case "Emrakul" -> "decks/converted/emrakul-1.dck";
                    case "Allies" -> "decks/pilot/Allies.dck";
                    default -> throw new IllegalArgumentException(testDeck);
                };
                var deck = CardUtil.getDeck(path, false, false, "", false, false);
                for (var entry : deck.getMain()) {
                    var card = entry.getKey();
                    check(Set.of("TLA", "TLE").contains(card.getEdition()), card.toString());
                    int needed = entry.getValue() - player.getCards().count(card);
                    if (needed > 0) player.getCards().add(card, needed);
                }
                var main = player.getSelectedDeck().getMain();
                main.clear();
                main.addAll(deck.getMain());
                System.out.println("PLAY player deck " + deck.getName());
                return null;
            });
        }
        if (Boolean.getBoolean("avatar.test.gear")) {
            render(() -> {
                var player = Current.player();
                for (String name : List.of("Armor of the Hivelord", "Black Lotus",
                        testDeck.equals("Allies") ? "Mox Pearl" : "Mox Emerald")) {
                    if (!player.hasItem(name)) check(player.addItem(name), name);
                    var item = player.getItems().stream().filter(i -> name.equals(i.name)).findFirst().orElseThrow();
                    player.equip(item);
                }
                System.out.println("PLAY equipped test hero");
                return null;
            });
        }
        int before=Current.player().getGold();
        var beforeCards=Current.player().getCollectionCards(true);
        render(()->{
            WorldStage.getInstance().loadPOI(location);
            return null;
        });
        Thread.sleep(1500);
        render(()->{var boss=tile.currentMap().getEnemyByID(bossId);
            check(boss!=null,bossName);tile.currentMap().beginDuel(boss);
            tile.currentMap().act(5f);tile.currentMap().act(1/60f);Gdx.graphics.requestRendering();return null;});
        var duel=render(DuelScene::instance);
        var hosted=DuelScene.class.getDeclaredField("hostedMatch");hosted.setAccessible(true);
        boolean finished=false,quit=false;
        int lastTurn = -1;
        deadline=System.currentTimeMillis()+600000;
        while(System.currentTimeMillis()<deadline){
            Thread.sleep(400);
            Gdx.graphics.requestRendering();
            if(Forge.getCurrentScene() instanceof RewardScene)break;
            if(quit && Forge.getCurrentScene()==tile){
                render(()->{tile.currentMap().act(0.5f);return null;});
            }
            if(render(()->{if(FOverlay.getTopOverlay() instanceof FOptionPane pane){pane.setResult(0);return true;}return false;}))continue;
            var match=(forge.gamemodes.match.HostedMatch)hosted.get(duel);
            if(match==null || match.getGame()==null)continue;
            var game=match.getGame();
            if(!finished && game.getPlayers().size()==2 && game.getAge()==forge.game.GameStage.Play && game.getPhaseHandler().getTurn()>0){
                var enemy=game.getPlayers().get(1);
                check(enemy.getName().contains(bossName),enemy.getName());
                check(game.getRules().getGamesPerMatch()==1,"factory match length");
                System.out.println( "PLAY duel "+enemy+" "+enemy.getRegisteredPlayer().getDeck().getName());
                var human=game.getPlayers().get(0);
                var ai=new forge.ai.PlayerControllerAi(game,human,forge.player.GamePlayerUtil.createAiPlayer("Avatar test pilot"));
                human.dangerouslySetController(ai);
                finished=true;
            }
            int turn = game.getPhaseHandler().getTurn();
            if (finished && turn != lastTurn) {
                lastTurn = turn;
                System.out.println("PLAY turn " + turn);
            }
            if(!game.isGameOver()){
                for(var controller:match.getHumanControllers())render(()->{controller.selectButtonOk();return null;});
            }
            if(finished && !quit && match.isMatchOver()){
                if(game.getMatch().getWinner().getPlayer().getName().contains(bossName)){
                    System.out.println("PLAY defeat at turn "+game.getPhaseHandler().getTurn());
                    System.exit(4);
                }
                quit=render(()->{
                    if(Forge.getCurrentScreen() instanceof forge.screens.match.MatchScreen screen && screen.getViewWinLose()!=null)
                        {System.out.println("PLAY result turn "+game.getPhaseHandler().getTurn()+" winner "+game.getMatch().getWinner().getPlayer().getName());return screen.getViewWinLose().getBtnQuit().trigger();}
                    return false;});
            }
        }
        check(Forge.getCurrentScene() instanceof RewardScene,"reward screen; current="+Forge.getCurrentScene()+" screen="+Forge.getCurrentScreen());
        var rewards=RewardScene.instance();var names=new ArrayList<String>();
        var gained=new HashMap<forge.item.PaperCard,Integer>();
        // getGeneratedRewards() only lists face-up cards. Loot enters the scene face-down.
        var generated = RewardScene.class.getDeclaredField("generated");
        generated.setAccessible(true);
        render(()->{for(var object:(com.badlogic.gdx.utils.Array<?>)generated.get(rewards)){
            if (!(object instanceof forge.adventure.util.RewardActor actor)) continue;
            var card=actor.getReward().getCard();if(card!=null){check(Set.of("TLA","TLE").contains(card.getEdition()),card.toString());names.add(card.getName()+"|"+card.getEdition());gained.merge(card,1,Integer::sum);}
        }return null;});
        check(!names.isEmpty(),"no card rewards");
        for(int i=0;i<10 && Forge.getCurrentScene()==rewards;i++){render(rewards::done);Thread.sleep(700);}
        check(dragon || Current.player().getGold()>before,"gold not credited");
        var afterCards=Current.player().getCollectionCards(true);
        for(var entry:gained.entrySet())check(afterCards.count(entry.getKey())>=beforeCards.count(entry.getKey())+entry.getValue(),"card missing "+entry);
        for (var entry : afterCards) {
            if (entry.getValue() > beforeCards.count(entry.getKey()))
                check(Set.of("TLA", "TLE").contains(entry.getKey().getEdition()), "unexpected collection gain " + entry);
        }
        System.out.println("PLAY reward cards "+names+" gold "+before+" -> "+Current.player().getGold());
    }
    public static void main(String[] args) throws Exception {
        TestProfile.require();
        new Thread(()->{try{test();System.exit(0);}catch(Throwable t){t.printStackTrace();System.exit(7);}},"AvatarTest").start();
        forge.app.Main.main(new String[]{"width=960","height=540"});
    }
}
