import com.badlogic.gdx.Gdx;
import forge.Forge;
import forge.adventure.scene.*;
import forge.adventure.stage.WorldStage;
import forge.adventure.util.*;
import forge.adventure.character.ShopActor;
import forge.adventure.world.WorldSave;
import forge.gamemodes.match.HostedMatch;
import forge.item.PaperCard;
import forge.toolbox.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.BooleanSupplier;

public class Playthrough {
    static <T> T ui(Callable<T> action) throws Exception {
        var future=new FutureTask<T>(action);
        Gdx.app.postRunnable(future);
        return future.get(120,TimeUnit.SECONDS);
    }
    static Object field(Object object,String name)throws Exception{
        var f=object.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return f.get(object);
    }
    static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    static void until(BooleanSupplier condition,String message)throws Exception{
        long limit=System.nanoTime()+TimeUnit.SECONDS.toNanos(160);
        while(!condition.getAsBoolean()){
            if(System.nanoTime()>limit)throw new AssertionError(message+" scene="+Forge.getCurrentScene());
            Thread.sleep(250);
        }
    }
    static String print(PaperCard c){
        check(Set.of("MH1","MH2","LTR").contains(c.getEdition()) || VerifyPlane.modern.containsKey(c.getName()+"|"+c.getEdition()),"foreign print "+c);
        return c.getName()+"|"+c.getEdition()+"|"+c.getArtIndex();
    }
    static Map<String,Integer> collection(){
        Map<String,Integer> rows=new TreeMap<>();
        for(var pc:Current.player().getCards().toFlatList())rows.merge(print(pc),1,Integer::sum);
        return rows;
    }
    static boolean coloredGeneralCard() throws Exception {
        var shop=(ShopActor)field(RewardScene.instance(),"shopActor");
        check(shop.getShopData().name.startsWith("RingTownColorless"),"wrong town vendor");
        // RewardScene sorts the six offers for display. Any colored offer in
        // this town must come from a general slot; local weights are tested in VerifyPlane.
        var offers=RewardScene.instance().getGeneratedRewards();
        check(offers.size()==6,"six displayed offers");
        var colored=offers.stream().map(a->a.getReward().getCard())
                .filter(c->!c.getRules().getColorIdentity().isColorless())
                .map(Playthrough::print).toList();
        check(colored.size()<=3,"too many colored cards "+colored);
        System.out.println("PLAY "+shop.getShopData().name+" colored general offers "+colored);
        return !colored.isEmpty();
    }
    static void run()throws Exception{
        until(()->Forge.afterDBloaded||Forge.getCurrentScene()!=null,"startup");
        if(Forge.getCurrentScene()==null)ui(()->{Forge.openAdventure();return null;});
        until(()->Forge.getCurrentScene() instanceof StartScene,"main menu");
        check(Config.instance().getPlane().equals("HorizonsRingEdited"),"plane");
        check(Path.of(WorldSave.getSaveDir()).toAbsolutePath().normalize().startsWith(Path.of("").toRealPath()),"profile");
        VerifyPlane.loadModern();
        ui(()->StartScene.instance().NewGame());
        until(()->Forge.getCurrentScene() instanceof NewGameScene,"new game menu");
        ui(()->{
            var scene=NewGameScene.instance();
            ((com.badlogic.gdx.scenes.scene2d.ui.TextField)field(scene,"selectedName")).setText("Horizons Test");
            var modes=(com.badlogic.gdx.utils.Array<?>)field(scene,"modes");
            int index=java.util.stream.IntStream.range(0,modes.size).filter(i->modes.get(i)==AdventureModes.Chaos).findFirst().orElse(-1);
            check(index>=0,"Chaos unavailable");
            ((Selector)field(scene,"mode")).setCurrentIndex(index);
            return scene.start();
        });
        until(()->Forge.getCurrentScene() instanceof GameScene || Forge.getCurrentScene() instanceof TileMapScene,"world generation");
        var tile=ui(TileMapScene::instance);
        if(Forge.getCurrentScene()==tile)ui(()->tile.currentMap().exitDungeon(false,false));
        var world=WorldSave.getCurrentSave();
        var starter=world.getPlayer().getSelectedDeck();
        check(starter.getMain().countAll()==60,"Chaos starter size");
        starter.getAllCardsInASinglePool().toFlatList().forEach(Playthrough::print);
        System.out.println("PLAY Chaos starter verified "+starter.getMain().countAll()+" cards, outside=0");
        var points=world.getWorld().getAllPointOfInterest();
        System.out.println("PLAY new world "+world.getPlayer().getName()+" POIs="+points.size());
        var town=points.stream().filter(p->p.getData().map.contains("/towns/waste_town")).findFirst().orElseThrow();
        ui(()->{Current.player().addShards(2);return null;});
        List<String> first=null;
        boolean seenColored=false;
        for(int visit=0;visit<3;visit++){
            check(Forge.getCurrentScene() instanceof GameScene,"world before town");
            ui(()->{WorldStage.getInstance().loadPOI(town);return null;});
            ui(()->{
                for(int id=0;id<300;id++)if(tile.currentMap().getByID(id) instanceof ShopActor shop && shop.getShopData().name.startsWith("RingTown") && shop.getShopData().rewards.size==6){
                    shop.onPlayerCollide();return null;
                }
                throw new AssertionError("town singles");
            });
            until(()->Forge.getCurrentScene() instanceof RewardScene,"shop entry");
            var stock=ui(()->RewardScene.instance().getGeneratedRewards().stream().map(a->print(a.getReward().getCard())).sorted().toList());
            check(stock.size()==6,"six singles "+stock);
            System.out.println("PLAY town "+town.getData().map+" visit "+visit+" "+stock);
            seenColored |= ui(Playthrough::coloredGeneralCard);
            if(first!=null)check(first.equals(stock),"restock");
            first=stock;
            if(visit==1){
                int balance=ui(()->Current.player().getShards());
                ui(()->{
                    var scene=RewardScene.instance();
                    var shop=(ShopActor)field(scene,"shopActor");
                    var button=(com.github.tommyettinger.textra.TextraButton)field(scene,"restockButton");
                    check(shop.getRestockPrice()==2 && button.isVisible() && !button.isDisabled(),"restock unavailable");
                    tile.currentMap().performTouch(button);
                    return null;
                });
                until(()->Current.player().getShards()==balance-2,"restock charge");
                System.out.println("PLAY shards "+balance+" -> "+Current.player().getShards());
                first=ui(()->RewardScene.instance().getGeneratedRewards().stream().map(a->print(a.getReward().getCard())).sorted().toList());
                check(first.size()==6,"rerolled stock");
                seenColored |= ui(Playthrough::coloredGeneralCard);
                System.out.println("PLAY refreshed "+first);
            }
            if(visit==2){
                for(boolean variants:new boolean[]{false,true}){
                    ui(()->{
                        Config.instance().getSettingData().useAllCardVariants=variants;
                        Current.player().giveGold(10000);
                        Current.player().addShards(400);
                        return null;
                    });
                    var scene=RewardScene.instance();
                    var restock=scene.getClass().getDeclaredMethod("restockShop");
                    restock.setAccessible(true);
                    for(int draw=0;;draw++){
                        check(draw<200,"no Modern offer");
                        var button=ui(()->{
                            restock.invoke(scene);
                            for(var actor:(com.badlogic.gdx.utils.Array<?>)field(scene,"generated")){
                                if(!actor.getClass().getSimpleName().equals("BuyButton"))continue;
                                var card=((Reward)field(actor,"reward")).getCard();
                                if(!Set.of("MH1","MH2","LTR").contains(card.getEdition()))
                                    return (com.github.tommyettinger.textra.TextraButton)actor;
                            }
                            return null;
                        });
                        if(button==null)continue;
                        String key=print(((Reward)field(button,"reward")).getCard());
                        int before=ui(()->collection().getOrDefault(key,0));
                        ui(()->{tile.currentMap().performTouch(button);return null;});
                        until(()->collection().getOrDefault(key,0)==before+1,"purchase "+key);
                        System.out.println("PLAY Modern purchase variants="+variants+" "+key);
                        break;
                    }
                }
            }
            ui(()->RewardScene.instance().done());
            until(()->Forge.getCurrentScene()==tile,"leave shop");
            ui(()->tile.currentMap().exitDungeon(false,false));
        }
        check(seenColored,"colorless town needs an observed colored general card");
        var skep=points.stream().filter(p->p.getData().name.equals("Skep")).findFirst().orElseThrow();
        ui(()->{WorldStage.getInstance().loadPOI(skep);return null;});
        var before=ui(Playthrough::collection);
        ui(()->{var stage=tile.currentMap();var boss=stage.getEnemyByID(57);
            check(boss!=null,"Skep boss");
            stage.beginDuel(boss);return null;});
        for(int i=0;i<160 && Forge.getCurrentScene()==tile;i++){
            ui(()->{tile.currentMap().act(.1f);return null;});
            Thread.sleep(100);
        }
        until(()->Forge.getCurrentScene() instanceof DuelScene,"boss duel");
        var duel=ui(DuelScene::instance);
        HostedMatch host=null;
        for(int i=0;i<200;i++){
            var box=(FOptionPane)field(duel,"bossDialogue");
            if(box!=null && box.isVisible())ui(()->{box.setResult(0);return null;});
            host=(HostedMatch)field(duel,"hostedMatch");
            if(host!=null && host.getGame()!=null && host.getGame().getPlayers().size()==2)break;
            Thread.sleep(300);
        }
        var game=host.getGame();
        var startedHost=host;
        for(int i=0;i<240 && game.getAge()!=forge.game.GameStage.Play;i++){
            ui(()->{
                if(FOverlay.getTopOverlay() instanceof FOptionPane box)box.setResult(0);
                for(var human:startedHost.getHumanControllers())human.selectButtonOk();
                return null;
            });
            Thread.sleep(250);
        }
        check(game.getAge()==forge.game.GameStage.Play,"game not ready "+game.getAge());
        var enemy=game.getPlayers().get(1);
        check(enemy.getName().contains("Sliver"),enemy.getName());
        enemy.concede();
        for(var human:host.getHumanControllers())human.selectButtonOk();
        game.getAction().checkGameOverCondition();
        until(()->game.getMatch().isMatchOver(),"match result");
        System.out.println("PLAY boss conceded; match complete");
        for(int i=0;i<120 && !(Forge.getCurrentScene() instanceof RewardScene);i++){
            ui(()->{if(FOverlay.getTopOverlay() instanceof forge.screens.match.winlose.ViewWinLose v)v.getBtnQuit().trigger();
                if(Forge.getCurrentScene()==tile)tile.currentMap().act(.2f);
                return null;});
            Thread.sleep(300);
        }
        until(()->Forge.getCurrentScene() instanceof RewardScene,"boss rewards");
        var prizes=ui(()->{
            var cards=new ArrayList<String>();
            for(Object actor:(com.badlogic.gdx.utils.Array<?>)field(RewardScene.instance(),"generated"))
                if(actor instanceof RewardActor a && a.getReward().getCard()!=null)cards.add(print(a.getReward().getCard()));
            return cards;
        });
        check(!prizes.isEmpty(),"no prize cards");
        ui(()->RewardScene.instance().done());
        Thread.sleep(1000);
        if(Forge.getCurrentScene() instanceof RewardScene)ui(()->RewardScene.instance().done());
        until(()->!(Forge.getCurrentScene() instanceof RewardScene),"collect");
        var after=ui(Playthrough::collection);
        Map<String,Integer> expected=new TreeMap<>(before);
        prizes.forEach(p->expected.merge(p,1,Integer::sum));
        check(expected.equals(after),"collection delta "+prizes);
        System.out.println("PLAY collected "+prizes);
    }
    public static void main(String[] args)throws Exception{
        new Thread(()->{try{run();System.exit(0);}catch(Throwable e){e.printStackTrace();System.exit(1);}}).start();
        forge.app.Main.main(new String[]{"width=960","height=540"});
    }
}
