import forge.adventure.util.*;
import forge.adventure.data.*;
import forge.gui.GuiBase;
import forge.model.FModel;
import forge.localinstance.properties.ForgeConstants;
import java.nio.file.*;
import java.util.*;

public class FindEmpty {
    static final Set<String> seen=new HashSet<>();
    static void inspect(EnemyData enemy) {
        if(enemy.rewards!=null) for(int i=0;i<enemy.rewards.length;i++) {
            var r=enemy.rewards[i];
            String type=r.type==null?"card":r.type;
            if(r.cardName!=null || !Set.of("card","randomCard","deckCard").contains(type))continue;
            for(String ref:enemy.deck) {
                var pool=type.equals("deckCard")?CardUtil.getDeck(ref,true,false,"",false,false).getMain().toFlatList():RewardData.getAllCards();
                if(CardUtil.getPredicateResult(pool,r).isEmpty()){
                    System.out.println("EMPTY\t"+enemy.name+"\t"+i);
                    break;
                }
            }
        }
        if(enemy.nextEnemy!=null)inspect(enemy.nextEnemy);
    }
    public static void main(String[] args)throws Exception {
        GuiBase.setInterface(new forge.GuiDesktop());FModel.initialize(null,null);
        var f=Path.of(ForgeConstants.USER_ADVENTURE_DIR,"settings.json").toAbsolutePath().normalize();
        if(!f.startsWith(Path.of("").toAbsolutePath()))throw new AssertionError(f);
        Files.createDirectories(f.getParent());Files.writeString(f,"{\"plane\":\"HorizonsRingEdited\"}");
        var cfg=Config.instance();
        AdventureOverrides.instance().load(cfg.getPrefix(),FModel.getMagicDb().getEditions(),cfg.getConfigData());
        Current.player().updateDifficulty(cfg.getConfigData().difficulties[0]);
        for(var e:WorldData.getAllEnemies())inspect(e);
        System.exit(0);
    }
}
